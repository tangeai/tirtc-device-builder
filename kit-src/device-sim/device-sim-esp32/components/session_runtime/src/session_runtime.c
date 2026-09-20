#include "session_runtime.h"

#include <stdio.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "esp_log.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "media_runtime.h"
#include "platform_client.h"
#include "runtime_config.h"
#include "tirtc_adapter.h"

#define SESSION_QUEUE_DEPTH 16
#define SESSION_ARGUMENT_MAX 1024
#define SESSION_PAYLOAD_MAX 4096
#define SESSION_CONNECT_TIMEOUT_MS 12000
#define SESSION_REQUEST_TIMEOUT_MS 17000
#define SESSION_RINGING_TIMEOUT_MS 45000
#define SESSION_CALLING_TIMEOUT_MS 30000
#define SESSION_AI_RESPONSE_TIMEOUT_MS 10000
#define SESSION_CONFIRM_TIMEOUT_MS 10000
#define VOIP_PROFILE_RETRY_MS 5000
#define VOIP_CANCEL_CACHE_MS 60000
#define ROOM_MISSING_CONFIRMATIONS 3U
#define CMD_VOIP_ACCEPT 0x2000U
#define CMD_VOIP_HANGUP 0x2001U
#define CMD_AI 0x2100U

typedef enum {
    EVENT_CONNECTION = 0,
    EVENT_COMMAND,
    EVENT_AI_TOKEN,
    EVENT_AI_PRESS,
    EVENT_AI_RELEASE,
    EVENT_PLATFORM_SIGNAL,
    EVENT_VOIP_CALL_DEFAULT,
    EVENT_VOIP_CALLERS_RESPONSE,
    EVENT_VOIP_DIAL_RESPONSE,
    EVENT_VOIP_CONNECT,
    EVENT_CONTACTS,
    EVENT_CONTACTS_RESPONSE,
    EVENT_CALL_REQUEST_RESPONSE,
    EVENT_ROOM_RESPONSE,
    EVENT_ACCEPT_RESPONSE,
    EVENT_CALL_DEFAULT,
    EVENT_DEVICE_CALL,
    EVENT_ACCEPT,
    EVENT_REJECT,
    EVENT_CANCEL,
    EVENT_HANGUP,
} session_event_type_t;

typedef struct {
    session_event_type_t type;
    bool connected;
    bool incoming;
    uint32_t command;
    uint32_t length;
    uint32_t connection_generation;
    uint32_t session_generation;
    char *first;
    char *second;
    char *payload;
} session_event_t;

typedef struct {
    session_event_type_t type;
    uint32_t session_generation;
} session_request_context_t;

typedef struct {
    char peer_id[SESSION_ARGUMENT_MAX];
    char token[SESSION_ARGUMENT_MAX];
    char room_id[129];
    char open_id[129];
    char call_id[65];
    char app_id[65];
    char model_id[65];
    char session_token[257];
    char payload[513];
    char from_device_id[65];
} voip_signal_t;

static const char *TAG = "session_runtime";
static QueueHandle_t s_queue;
static TaskHandle_t s_task;
static volatile device_session_state_t s_state = DEVICE_SESSION_OFFLINE;
static volatile device_service_t s_service = DEVICE_SERVICE_H5;
static int64_t s_ai_start_at_ms;
static char s_ai_role_id[65];
static char s_call_room_id[129];
static char s_call_peer_id[65];
static bool s_call_after_contacts;
static bool s_call_outgoing;
static atomic_bool s_room_request_pending;
static int64_t s_next_room_poll_ms;
static unsigned s_room_missing_count;
static int64_t s_session_deadline_ms;
static uint32_t s_session_generation = 1;
static uint32_t s_bound_connection_generation;
static atomic_bool s_voip_profile_submitted;
static atomic_bool s_voip_profile_pending;
static atomic_int_fast64_t s_voip_profile_retry_at_ms;
static bool s_voip_outgoing;
static bool s_voip_connect_submitted;
static char s_voip_peer_id[SESSION_ARGUMENT_MAX];
static char s_voip_token[SESSION_ARGUMENT_MAX];
static char s_voip_room_id[129];
static char s_voip_open_id[129];
static char s_voip_call_id[65];
static char s_voip_app_id[65];
static char s_voip_model_id[65];
static char s_voip_session_token[257];
static char s_voip_payload[513];
static char s_voip_cancelled_open_id[129];
static char s_voip_cancelled_call_id[65];
static int64_t s_voip_cancelled_until_ms;

static void remember_cancelled_voip(void);

static int64_t now_ms(void)
{
    return esp_timer_get_time() / 1000;
}

static void release_event(session_event_t *event)
{
    if (event == NULL) {
        return;
    }
    free(event->first);
    free(event->second);
    free(event->payload);
    memset(event, 0, sizeof(*event));
}

static bool copy_event_text(char **destination,
                            uint32_t *copied_length,
                            const void *source,
                            size_t length,
                            size_t maximum)
{
    if (source == NULL || length == 0) {
        return true;
    }
    size_t count = length < maximum - 1U ? length : maximum - 1U;
    char *text = malloc(count + 1U);
    if (text == NULL) {
        return false;
    }
    memcpy(text, source, count);
    text[count] = '\0';
    *destination = text;
    if (copied_length != NULL) {
        *copied_length = (uint32_t)count;
    }
    return true;
}

static bool queue_event(const session_event_t *event)
{
    return s_queue != NULL && xQueueSend(s_queue, event, 0) == pdTRUE;
}

static void adapter_connection_changed(bool connected,
                                       bool incoming,
                                       uint32_t connection_generation,
                                       uint32_t request_tag,
                                       void *user_data)
{
    (void)user_data;
    session_event_t event = {
        .type = EVENT_CONNECTION,
        .connected = connected,
        .incoming = incoming,
        .connection_generation = connection_generation,
        .session_generation = request_tag,
    };
    if (!queue_event(&event)) {
        ESP_LOGW(TAG, "dropping connection event because session queue is full");
    }
}

static void adapter_command(uint32_t command,
                            const void *data,
                            uint32_t length,
                            uint32_t connection_generation,
                            void *user_data)
{
    (void)user_data;
    session_event_t event = {
        .type = EVENT_COMMAND,
        .command = command,
        .connection_generation = connection_generation,
    };
    if (!copy_event_text(&event.payload,
                         &event.length,
                         data,
                         length,
                         SESSION_PAYLOAD_MAX)) {
        ESP_LOGW(TAG, "cannot allocate command payload");
        return;
    }
    if (!queue_event(&event)) {
        ESP_LOGW(TAG, "dropping command event because session queue is full");
        release_event(&event);
    }
}

static void platform_signal(const char *json, size_t length, void *user_data)
{
    (void)user_data;
    session_event_t event = {
        .type = EVENT_PLATFORM_SIGNAL,
    };
    if (!copy_event_text(&event.payload,
                         &event.length,
                         json,
                         length,
                         SESSION_PAYLOAD_MAX)) {
        ESP_LOGW(TAG, "cannot allocate platform signal payload");
        return;
    }
    if (!queue_event(&event)) {
        ESP_LOGW(TAG, "dropping platform signal because session queue is full");
        release_event(&event);
    }
}

static void service_event_response(const char *body, void *user_data)
{
    session_request_context_t *context = user_data;
    if (context == NULL) {
        return;
    }
    if (context->type == EVENT_ROOM_RESPONSE) {
        atomic_store_explicit(&s_room_request_pending, false, memory_order_release);
    }
    session_event_t event = {
        .type = context->type,
        .session_generation = context->session_generation,
    };
    if (body != NULL &&
        !copy_event_text(&event.payload,
                         &event.length,
                         body,
                         strlen(body),
                         SESSION_PAYLOAD_MAX)) {
        ESP_LOGW(TAG, "cannot allocate service response payload");
        free(context);
        return;
    }
    if (!queue_event(&event)) {
        ESP_LOGW(TAG, "dropping service response because session queue is full");
        release_event(&event);
    }
    free(context);
}

static void service_log_response(const char *body, void *user_data)
{
    const char *operation = user_data == NULL ? "operation" : (const char *)user_data;
    if (body == NULL || body[0] == '\0') {
        ESP_LOGW(TAG, "%s returned no response body", operation);
        return;
    }
    cJSON *root = cJSON_Parse(body);
    const cJSON *code = root == NULL ? NULL : cJSON_GetObjectItemCaseSensitive(root, "code");
    if (!cJSON_IsNumber(code) || (code->valueint != 0 && code->valueint != 200)) {
        ESP_LOGW(TAG, "%s was not acknowledged", operation);
    }
    cJSON_Delete(root);
}

static bool response_data(const char *body, cJSON **root_out, const cJSON **data_out)
{
    cJSON *root = body == NULL ? NULL : cJSON_Parse(body);
    const cJSON *code = root == NULL ? NULL : cJSON_GetObjectItemCaseSensitive(root, "code");
    const cJSON *data = root == NULL ? NULL : cJSON_GetObjectItemCaseSensitive(root, "data");
    bool ok = cJSON_IsNumber(code) && (code->valueint == 0 || code->valueint == 200);
    if (!ok) {
        cJSON_Delete(root);
        return false;
    }
    *root_out = root;
    *data_out = data;
    return true;
}

static int submit_service_event_timeout(session_event_type_t response_event,
                                        platform_service_t service,
                                        const char *path,
                                        const char *json_body,
                                        unsigned timeout_ms)
{
    session_request_context_t *context = malloc(sizeof(*context));
    if (context == NULL) {
        return ESP_ERR_NO_MEM;
    }
    context->type = response_event;
    context->session_generation = s_session_generation;
    int rc = platform_client_request_timeout(service,
                                             path,
                                             json_body,
                                             timeout_ms,
                                             service_event_response,
                                             context);
    if (rc != ESP_OK) {
        free(context);
    }
    return rc;
}

static int submit_service_event(session_event_type_t response_event,
                                platform_service_t service,
                                const char *path,
                                const char *json_body)
{
    return submit_service_event_timeout(response_event,
                                        service,
                                        path,
                                        json_body,
                                        15000U);
}

static int submit_room_action_for(const char *path,
                                  const char *room_id,
                                  const char *reason)
{
    if (room_id == NULL || room_id[0] == '\0') {
        return -1;
    }
    cJSON *root = cJSON_CreateObject();
    if (root == NULL || !cJSON_AddStringToObject(root, "room_id", room_id) ||
        (reason != NULL && !cJSON_AddStringToObject(root, "reason", reason))) {
        cJSON_Delete(root);
        return -1;
    }
    char *body = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (body == NULL) {
        return -1;
    }
    int rc = platform_client_request(PLATFORM_SERVICE_CALL,
                                     path,
                                     body,
                                     service_log_response,
                                     (void *)path);
    free(body);
    return rc;
}

static int submit_room_action(const char *path, const char *reason)
{
    return submit_room_action_for(path, s_call_room_id, reason);
}

static void set_state(device_session_state_t state, device_service_t service)
{
    ESP_LOGI(TAG,
             "state %s -> %s service=%s",
             device_session_state_name(s_state),
             device_session_state_name(state),
             device_service_name(service));
    s_state = state;
    s_service = service;
}

static void advance_session_generation(void)
{
    s_session_generation++;
    if (s_session_generation == 0) {
        s_session_generation = 1;
    }
    s_bound_connection_generation = 0;
}

static void begin_session(device_session_state_t state, device_service_t service)
{
    advance_session_generation();
    s_session_deadline_ms = 0;
    s_room_missing_count = 0;
    set_state(state, service);
}

static void finish_session(void)
{
    if (s_service == DEVICE_SERVICE_VOIP &&
        (s_voip_call_id[0] != '\0' ||
         (s_voip_outgoing && s_voip_open_id[0] != '\0'))) {
        remember_cancelled_voip();
    }
    media_runtime_set_uplink_active(false);
    /* Disconnect also invalidates a pending WHIP/P2P request. The adapter does
     * not echo a local disconnect event back into this state machine. */
    (void)tirtc_adapter_disconnect();
    advance_session_generation();
    s_ai_start_at_ms = 0;
    s_ai_role_id[0] = '\0';
    s_session_deadline_ms = 0;
    s_call_room_id[0] = '\0';
    s_call_peer_id[0] = '\0';
    s_call_after_contacts = false;
    s_call_outgoing = false;
    s_room_missing_count = 0;
    s_voip_outgoing = false;
    s_voip_connect_submitted = false;
    s_voip_peer_id[0] = '\0';
    s_voip_token[0] = '\0';
    s_voip_room_id[0] = '\0';
    s_voip_open_id[0] = '\0';
    s_voip_call_id[0] = '\0';
    s_voip_app_id[0] = '\0';
    s_voip_model_id[0] = '\0';
    s_voip_session_token[0] = '\0';
    s_voip_payload[0] = '\0';
    set_state(DEVICE_SESSION_IDLE, DEVICE_SERVICE_H5);
}

static bool copy_json_string(const cJSON *object,
                             const char *name,
                             char *destination,
                             size_t destination_size)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (!cJSON_IsString(item) || item->valuestring == NULL ||
        item->valuestring[0] == '\0' || strlen(item->valuestring) >= destination_size) {
        return false;
    }
    (void)snprintf(destination, destination_size, "%s", item->valuestring);
    return true;
}

static void copy_optional_json_string(const cJSON *object,
                                      const char *name,
                                      char *destination,
                                      size_t destination_size)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    destination[0] = '\0';
    if (cJSON_IsString(item) && item->valuestring != NULL) {
        (void)snprintf(destination, destination_size, "%.*s",
                       (int)destination_size - 1, item->valuestring);
    }
}

static bool parse_voip_signal(const cJSON *payload, voip_signal_t *signal)
{
    if (!cJSON_IsObject(payload) || signal == NULL) {
        return false;
    }
    memset(signal, 0, sizeof(*signal));
    bool valid = copy_json_string(payload,
                                  "peer_id",
                                  signal->peer_id,
                                  sizeof(signal->peer_id)) &&
                 copy_json_string(payload,
                                  "token",
                                  signal->token,
                                  sizeof(signal->token));
    copy_optional_json_string(payload,
                              "wx_room_id",
                              signal->room_id,
                              sizeof(signal->room_id));
    copy_optional_json_string(payload,
                              "wx_user_openid",
                              signal->open_id,
                              sizeof(signal->open_id));
    copy_optional_json_string(payload,
                              "wx_call_id",
                              signal->call_id,
                              sizeof(signal->call_id));
    copy_optional_json_string(payload,
                              "wx_app_id",
                              signal->app_id,
                              sizeof(signal->app_id));
    copy_optional_json_string(payload,
                              "wx_model_id",
                              signal->model_id,
                              sizeof(signal->model_id));
    copy_optional_json_string(payload,
                              "wx_server_token",
                              signal->session_token,
                              sizeof(signal->session_token));
    copy_optional_json_string(payload,
                              "wx_payload",
                              signal->payload,
                              sizeof(signal->payload));
    copy_optional_json_string(payload,
                              "wx_from",
                              signal->from_device_id,
                              sizeof(signal->from_device_id));
    return valid && signal->room_id[0] != '\0';
}

static void store_voip_signal(const voip_signal_t *signal)
{
    if (signal == NULL) {
        return;
    }
    (void)snprintf(s_voip_peer_id, sizeof(s_voip_peer_id), "%s", signal->peer_id);
    (void)snprintf(s_voip_token, sizeof(s_voip_token), "%s", signal->token);
    (void)snprintf(s_voip_room_id, sizeof(s_voip_room_id), "%s", signal->room_id);
    (void)snprintf(s_voip_open_id, sizeof(s_voip_open_id), "%s", signal->open_id);
    (void)snprintf(s_voip_call_id, sizeof(s_voip_call_id), "%s", signal->call_id);
    (void)snprintf(s_voip_app_id, sizeof(s_voip_app_id), "%s", signal->app_id);
    (void)snprintf(s_voip_model_id, sizeof(s_voip_model_id), "%s", signal->model_id);
    (void)snprintf(s_voip_session_token,
                   sizeof(s_voip_session_token),
                   "%s",
                   signal->session_token);
    (void)snprintf(s_voip_payload, sizeof(s_voip_payload), "%s", signal->payload);
}

static void reject_voip_values(const char *app_id,
                               const char *model_id,
                               const char *session_token,
                               const char *room_id,
                               const char *payload,
                               int reason)
{
    if (app_id == NULL || app_id[0] == '\0' ||
        model_id == NULL || model_id[0] == '\0' ||
        room_id == NULL || room_id[0] == '\0') {
        return;
    }
    cJSON *root = cJSON_CreateObject();
    bool ok = root != NULL &&
              cJSON_AddStringToObject(root, "wx_app_id", app_id) &&
              cJSON_AddStringToObject(root, "wx_model_id", model_id) &&
              cJSON_AddStringToObject(root,
                                     "wx_session_token",
                                     session_token == NULL ? "" : session_token) &&
              cJSON_AddStringToObject(root, "wx_room_id", room_id) &&
              cJSON_AddStringToObject(root,
                                     "wx_payload",
                                     payload == NULL ? "" : payload) &&
              cJSON_AddNumberToObject(root, "hangup_reason", reason);
    char *body = ok ? cJSON_PrintUnformatted(root) : NULL;
    cJSON_Delete(root);
    if (body == NULL) {
        ESP_LOGW(TAG, "cannot build VoIP reject request");
        return;
    }
    int rc = tirtc_adapter_service_request("/v1/wxvoip/reject",
                                           body,
                                           NULL,
                                           service_log_response,
                                           (void *)"voip reject");
    free(body);
    if (rc != 0) {
        ESP_LOGW(TAG, "VoIP reject submission failed rc=%d", rc);
    }
}

static void reject_voip_signal(int reason)
{
    reject_voip_values(s_voip_app_id,
                       s_voip_model_id,
                       s_voip_session_token,
                       s_voip_room_id,
                       s_voip_payload,
                       reason);
}

static void reject_voip_message(const voip_signal_t *signal, int reason)
{
    if (signal == NULL) {
        return;
    }
    reject_voip_values(signal->app_id,
                       signal->model_id,
                       signal->session_token,
                       signal->room_id,
                       signal->payload,
                       reason);
}

static void remember_cancelled_voip(void)
{
    (void)snprintf(s_voip_cancelled_open_id,
                   sizeof(s_voip_cancelled_open_id),
                   "%s",
                   s_voip_open_id);
    (void)snprintf(s_voip_cancelled_call_id,
                   sizeof(s_voip_cancelled_call_id),
                   "%s",
                   s_voip_call_id);
    s_voip_cancelled_until_ms = now_ms() + VOIP_CANCEL_CACHE_MS;
}

static void handle_platform_signal(const session_event_t *event)
{
    cJSON *root = cJSON_ParseWithLength(event->payload, event->length);
    const cJSON *type = root == NULL
                            ? NULL
                            : cJSON_GetObjectItemCaseSensitive(root, "type");
    const cJSON *channel = root == NULL
                               ? NULL
                               : cJSON_GetObjectItemCaseSensitive(root, "channel");
    const cJSON *payload = root == NULL
                               ? NULL
                               : cJSON_GetObjectItemCaseSensitive(root, "payload");
    const char *type_name = cJSON_IsString(type) ? type->valuestring : "";
    const char *channel_name = cJSON_IsString(channel) ? channel->valuestring : "";
    if (strcmp(type_name, "unbind") == 0) {
        ESP_LOGW(TAG,
                 "device unbound; clearing NVS credentials and restarting verification binding");
        finish_session();
        cJSON_Delete(root);
        esp_err_t err = runtime_config_clear_tirtc();
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "cannot clear binding credentials: %s", esp_err_to_name(err));
            return;
        }
        vTaskDelay(pdMS_TO_TICKS(500));
        esp_restart();
        return;
    }
    if (!cJSON_IsObject(payload)) {
        cJSON_Delete(root);
        return;
    }

    if (strcmp(channel_name, "device") == 0 &&
        strcmp(type_name, "call_incoming") == 0) {
        char room_id[sizeof(s_call_room_id)] = {0};
        char caller_id[sizeof(s_call_peer_id)] = {0};
        bool valid = copy_json_string(payload, "room_id", room_id, sizeof(room_id)) &&
                     copy_json_string(payload, "caller_id", caller_id,
                                      sizeof(caller_id));
        bool duplicate = valid && s_service == DEVICE_SERVICE_CALL &&
                         s_call_room_id[0] != '\0' &&
                         strcmp(room_id, s_call_room_id) == 0;
        if (duplicate) {
            ESP_LOGI(TAG, "ignoring duplicate device call signal room=%s", room_id);
        } else if (valid && (s_state == DEVICE_SESSION_IDLE ||
                            s_state == DEVICE_SESSION_H5_STREAMING)) {
            if (tirtc_adapter_has_connection()) {
                media_runtime_set_uplink_active(false);
                (void)tirtc_adapter_disconnect();
            }
            (void)snprintf(s_call_room_id, sizeof(s_call_room_id), "%s", room_id);
            (void)snprintf(s_call_peer_id, sizeof(s_call_peer_id), "%s", caller_id);
            begin_session(DEVICE_SESSION_RINGING, DEVICE_SERVICE_CALL);
            s_call_outgoing = false;
            s_session_deadline_ms = now_ms() + SESSION_RINGING_TIMEOUT_MS;
            ESP_LOGI(TAG, "incoming device call from=%s room=%s; use accept or reject",
                     caller_id, room_id);
        } else if (valid) {
            ESP_LOGW(TAG, "device call arrived while busy; room=%s", room_id);
            (void)submit_room_action_for("/v1/call/reject", room_id, "busy");
        }
    } else if (strcmp(channel_name, "device") == 0 &&
               (strcmp(type_name, "room_cancel") == 0 ||
                strcmp(type_name, "call_reject") == 0)) {
        char room_id[sizeof(s_call_room_id)] = {0};
        (void)copy_json_string(payload, "room_id", room_id, sizeof(room_id));
        if (s_service == DEVICE_SERVICE_CALL && s_call_room_id[0] != '\0' &&
            strcmp(room_id, s_call_room_id) == 0) {
            ESP_LOGI(TAG, "device call ended by platform signal room=%s", room_id);
            finish_session();
        }
    } else if (strcmp(channel_name, "device") == 0 &&
               strcmp(type_name, "callee_answered") == 0) {
        char room_id[sizeof(s_call_room_id)] = {0};
        char callee_id[sizeof(s_call_peer_id)] = {0};
        (void)copy_json_string(payload, "room_id", room_id, sizeof(room_id));
        (void)copy_json_string(payload, "callee_id", callee_id, sizeof(callee_id));
        if (s_service == DEVICE_SERVICE_CALL && s_call_outgoing &&
            s_state == DEVICE_SESSION_CALLING &&
            s_call_room_id[0] != '\0' &&
            strcmp(room_id, s_call_room_id) == 0) {
            ESP_LOGI(TAG,
                     "callee answered device call callee=%s room=%s; waiting for P2P",
                     callee_id[0] == '\0' ? s_call_peer_id : callee_id,
                     room_id);
            s_session_deadline_ms = now_ms() + SESSION_CONNECT_TIMEOUT_MS;
        }
    } else if (strcmp(channel_name, "wx") == 0 &&
               strcmp(type_name, "call_incoming") == 0) {
        voip_signal_t signal;
        bool valid = parse_voip_signal(payload, &signal);
        bool open_id_matches = signal.open_id[0] == '\0' ||
                               strcmp(signal.open_id, s_voip_open_id) == 0;
        runtime_tirtc_config_t runtime = {0};
        bool from_this_device =
            signal.from_device_id[0] != '\0' &&
            runtime_config_load_tirtc(&runtime) == ESP_OK &&
            strcmp(signal.from_device_id, runtime.device_id) == 0;
        bool cancelled = false;
        if (now_ms() < s_voip_cancelled_until_ms) {
            if (s_voip_cancelled_call_id[0] != '\0') {
                cancelled = signal.call_id[0] != '\0' &&
                            strcmp(signal.call_id,
                                   s_voip_cancelled_call_id) == 0;
            } else if (s_voip_cancelled_open_id[0] != '\0') {
                cancelled =
                    from_this_device &&
                    (signal.open_id[0] == '\0' ||
                     strcmp(signal.open_id,
                            s_voip_cancelled_open_id) == 0);
            }
        }
        bool outgoing = valid && s_service == DEVICE_SERVICE_VOIP &&
                        s_state == DEVICE_SESSION_CALLING &&
                        (s_voip_call_id[0] != '\0'
                             ? (signal.call_id[0] != '\0' &&
                                strcmp(signal.call_id, s_voip_call_id) == 0 &&
                                open_id_matches)
                             : (signal.call_id[0] != '\0'
                                    ? (from_this_device && open_id_matches)
                                    : open_id_matches));
        bool recover_outgoing =
            valid &&
            (s_state == DEVICE_SESSION_IDLE ||
             s_state == DEVICE_SESSION_H5_STREAMING) &&
            signal.call_id[0] != '\0' && from_this_device;
        bool duplicate = valid && s_service == DEVICE_SERVICE_VOIP &&
                         s_voip_room_id[0] != '\0' &&
                         strcmp(signal.room_id, s_voip_room_id) == 0 &&
                         (s_state == DEVICE_SESSION_RINGING ||
                          s_state == DEVICE_SESSION_CALLING ||
                          s_state == DEVICE_SESSION_IN_CALL);

        if (!valid) {
            ESP_LOGW(TAG, "ignoring malformed VoIP call signal");
            reject_voip_message(&signal, 7);
        } else if (cancelled) {
            ESP_LOGI(TAG, "rejecting callback for a locally cancelled VoIP call");
            reject_voip_message(&signal, 7);
        } else if (duplicate) {
            ESP_LOGI(TAG, "ignoring duplicate VoIP call signal room=%s",
                     signal.room_id);
        } else if (outgoing || recover_outgoing) {
            store_voip_signal(&signal);
            if (recover_outgoing && tirtc_adapter_has_connection()) {
                media_runtime_set_uplink_active(false);
                (void)tirtc_adapter_disconnect();
            }
            if (recover_outgoing) {
                begin_session(DEVICE_SESSION_CALLING, DEVICE_SERVICE_VOIP);
                s_voip_outgoing = true;
                ESP_LOGI(TAG,
                         "recovering VoIP outgoing call after HTTP response loss");
            } else {
                ESP_LOGI(TAG, "VoIP callee answered; establishing WHIP connection");
            }
            if (tirtc_adapter_whip_connect(s_voip_peer_id,
                                           s_voip_token,
                                           s_session_generation) != 0) {
                finish_session();
            } else {
                s_voip_connect_submitted = true;
                s_session_deadline_ms = now_ms() + SESSION_CONNECT_TIMEOUT_MS;
            }
        } else if (s_state == DEVICE_SESSION_IDLE ||
                   s_state == DEVICE_SESSION_H5_STREAMING) {
            if (tirtc_adapter_has_connection()) {
                media_runtime_set_uplink_active(false);
                (void)tirtc_adapter_disconnect();
            }
            store_voip_signal(&signal);
            begin_session(DEVICE_SESSION_RINGING, DEVICE_SERVICE_VOIP);
            s_voip_outgoing = false;
            s_session_deadline_ms = now_ms() + SESSION_RINGING_TIMEOUT_MS;
            ESP_LOGI(TAG, "incoming VoIP call room=%s; use accept or reject",
                     s_voip_room_id);
        } else {
            ESP_LOGW(TAG, "VoIP call arrived while busy; rejecting");
            reject_voip_message(&signal, 5);
        }
    } else if (strcmp(channel_name, "wx") == 0 &&
               strcmp(type_name, "call_cancel") == 0 &&
               s_service == DEVICE_SERVICE_VOIP) {
        char room_id[sizeof(s_voip_room_id)] = {0};
        copy_optional_json_string(payload, "wx_room_id", room_id, sizeof(room_id));
        if (room_id[0] != '\0' && s_voip_room_id[0] != '\0' &&
            strcmp(room_id, s_voip_room_id) == 0) {
            ESP_LOGI(TAG, "VoIP call cancelled by remote room=%s", room_id);
            finish_session();
        } else {
            ESP_LOGW(TAG,
                     "ignoring stale VoIP cancel room=%s active=%s",
                     room_id,
                     s_voip_room_id);
        }
    }
    cJSON_Delete(root);
}

static void request_contacts(bool call_first)
{
    if (!platform_client_ready()) {
        ESP_LOGW(TAG, "contacts unavailable while platform signaling is offline");
        return;
    }
    if (tirtc_adapter_state() != TIRTC_ADAPTER_RUNNING) {
        ESP_LOGW(TAG, "contacts unavailable before TiRTC is running");
        return;
    }
    s_call_after_contacts = call_first;
    if (submit_service_event(EVENT_CONTACTS_RESPONSE,
                             PLATFORM_SERVICE_CALL,
                             "/v1/call/device/contacts",
                             NULL) != 0) {
        s_call_after_contacts = false;
        ESP_LOGE(TAG, "contacts request submission failed");
    }
}

static void request_device_call(const char *target_id)
{
    cJSON *root = cJSON_CreateObject();
    cJSON *targets = cJSON_CreateArray();
    cJSON *target = cJSON_CreateString(target_id);
    if (root == NULL || targets == NULL || target == NULL) {
        cJSON_Delete(target);
        cJSON_Delete(targets);
        cJSON_Delete(root);
        finish_session();
        return;
    }
    cJSON_AddItemToArray(targets, target);
    cJSON_AddItemToObject(root, "targets", targets);
    bool ok = cJSON_AddStringToObject(root, "call_type", "audio");
    char *body = ok ? cJSON_PrintUnformatted(root) : NULL;
    cJSON_Delete(root);
    if (body == NULL) {
        finish_session();
        return;
    }

    if (tirtc_adapter_has_connection()) {
        media_runtime_set_uplink_active(false);
        (void)tirtc_adapter_disconnect();
    }
    (void)snprintf(s_call_peer_id, sizeof(s_call_peer_id), "%s", target_id);
    begin_session(DEVICE_SESSION_CALLING, DEVICE_SERVICE_CALL);
    s_call_outgoing = true;
    s_session_deadline_ms = now_ms() + SESSION_REQUEST_TIMEOUT_MS;
    int rc = submit_service_event(EVENT_CALL_REQUEST_RESPONSE,
                                  PLATFORM_SERVICE_CALL,
                                  "/v1/call/request",
                                  body);
    free(body);
    if (rc != 0) {
        ESP_LOGE(TAG, "device call request submission failed rc=%d", rc);
        finish_session();
    }
}

static void handle_contacts_response(const char *body)
{
    const bool call_first = s_call_after_contacts;
    s_call_after_contacts = false;
    cJSON *root = NULL;
    const cJSON *data = NULL;
    if (!response_data(body, &root, &data)) {
        ESP_LOGE(TAG, "contacts response is invalid");
        return;
    }
    const cJSON *contacts = cJSON_IsObject(data)
                                ? cJSON_GetObjectItemCaseSensitive(data, "contacts")
                                : NULL;
    if (!cJSON_IsArray(contacts) || cJSON_GetArraySize(contacts) == 0) {
        ESP_LOGW(TAG, "contact list is empty");
        cJSON_Delete(root);
        return;
    }

    char first_id[sizeof(s_call_peer_id)] = {0};
    const cJSON *contact = NULL;
    int index = 0;
    cJSON_ArrayForEach(contact, contacts) {
        const cJSON *id = cJSON_GetObjectItemCaseSensitive(contact, "device_id");
        const cJSON *remark = cJSON_GetObjectItemCaseSensitive(contact, "remark");
        const cJSON *online = cJSON_GetObjectItemCaseSensitive(contact, "online");
        if (!cJSON_IsString(id) || id->valuestring == NULL) {
            continue;
        }
        ESP_LOGI(TAG, "contact[%d] id=%s remark=%s online=%s",
                 index++,
                 id->valuestring,
                 cJSON_IsString(remark) ? remark->valuestring : "-",
                 cJSON_IsTrue(online) ? "yes" : "no");
        if (first_id[0] == '\0' && strlen(id->valuestring) < sizeof(first_id)) {
            (void)snprintf(first_id, sizeof(first_id), "%s", id->valuestring);
        }
    }
    cJSON_Delete(root);
    if (call_first) {
        if (first_id[0] == '\0') {
            ESP_LOGW(TAG, "no usable contact to call");
        } else {
            ESP_LOGI(TAG, "calling first contact: %s", first_id);
            request_device_call(first_id);
        }
    }
}

static void handle_call_request_response(const char *body)
{
    if ((s_state != DEVICE_SESSION_CALLING &&
         s_state != DEVICE_SESSION_IN_CALL) ||
        s_service != DEVICE_SERVICE_CALL || !s_call_outgoing) {
        return;
    }
    cJSON *root = NULL;
    const cJSON *data = NULL;
    bool ok = response_data(body, &root, &data) && cJSON_IsObject(data) &&
              copy_json_string(data,
                               "room_id",
                               s_call_room_id,
                               sizeof(s_call_room_id));
    cJSON_Delete(root);
    if (!ok) {
        if (s_state == DEVICE_SESSION_IN_CALL) {
            ESP_LOGW(TAG,
                     "ignoring failed device call response because media is already connected");
            return;
        }
        ESP_LOGE(TAG, "device call request was rejected");
        finish_session();
        return;
    }
    if (s_state == DEVICE_SESSION_CALLING) {
        s_session_deadline_ms = now_ms() + SESSION_CALLING_TIMEOUT_MS;
    }
    s_next_room_poll_ms = now_ms();
    if (s_state == DEVICE_SESSION_CALLING) {
        ESP_LOGI(TAG, "calling room=%s; cancel automatically after 30 seconds",
                 s_call_room_id);
    } else {
        ESP_LOGI(TAG, "device call response synchronized room=%s",
                 s_call_room_id);
    }
}

static void handle_room_response(const char *body)
{
    cJSON *root = NULL;
    const cJSON *data = NULL;
    if (!response_data(body, &root, &data)) {
        ESP_LOGW(TAG, "room query response is invalid");
        return;
    }
    if (data == NULL || cJSON_IsNull(data)) {
        cJSON_Delete(root);
        if (s_service == DEVICE_SERVICE_CALL &&
            (s_state == DEVICE_SESSION_RINGING || s_state == DEVICE_SESSION_IN_CALL ||
             (s_state == DEVICE_SESSION_CALLING && s_call_room_id[0] != '\0'))) {
            s_room_missing_count++;
            if (s_room_missing_count >= ROOM_MISSING_CONFIRMATIONS) {
                ESP_LOGI(TAG,
                         "call room absent in %u consecutive fallback queries; closing",
                         s_room_missing_count);
                finish_session();
            } else {
                ESP_LOGW(TAG,
                         "call room temporarily absent in fallback query %u/%u",
                         s_room_missing_count,
                         ROOM_MISSING_CONFIRMATIONS);
            }
        }
        return;
    }
    s_room_missing_count = 0;

    char room_id[sizeof(s_call_room_id)] = {0};
    char caller_id[sizeof(s_call_peer_id)] = {0};
    char role[16] = {0};
    char status[24] = {0};
    bool ok = cJSON_IsObject(data) &&
              copy_json_string(data, "room_id", room_id, sizeof(room_id)) &&
              copy_json_string(data, "role", role, sizeof(role));
    (void)copy_json_string(data, "caller", caller_id, sizeof(caller_id));
    (void)copy_json_string(data, "status", status, sizeof(status));
    if (!ok) {
        cJSON_Delete(root);
        ESP_LOGW(TAG, "room response has no usable room or role");
        return;
    }

    if (strcmp(role, "callee") == 0 &&
        (s_state == DEVICE_SESSION_IDLE || s_state == DEVICE_SESSION_H5_STREAMING)) {
        if (tirtc_adapter_has_connection()) {
            media_runtime_set_uplink_active(false);
            (void)tirtc_adapter_disconnect();
        }
        (void)snprintf(s_call_room_id, sizeof(s_call_room_id), "%s", room_id);
        (void)snprintf(s_call_peer_id, sizeof(s_call_peer_id), "%s", caller_id);
        begin_session(DEVICE_SESSION_RINGING, DEVICE_SERVICE_CALL);
        s_call_outgoing = false;
        s_session_deadline_ms = now_ms() + SESSION_RINGING_TIMEOUT_MS;
        ESP_LOGI(TAG, "incoming device call from=%s room=%s; use accept or reject",
                 s_call_peer_id,
                 s_call_room_id);
    }
    cJSON_Delete(root);
}

static void accept_device_call(void)
{
    cJSON *root = cJSON_CreateObject();
    bool ok = root != NULL && s_call_peer_id[0] != '\0' && s_call_room_id[0] != '\0' &&
              cJSON_AddStringToObject(root, "device_id", s_call_peer_id) &&
              cJSON_AddStringToObject(root, "room_id", s_call_room_id) &&
              cJSON_AddStringToObject(root, "purpose", "call");
    char *body = ok ? cJSON_PrintUnformatted(root) : NULL;
    cJSON_Delete(root);
    if (body == NULL) {
        ESP_LOGE(TAG, "cannot build device accept request");
        finish_session();
        return;
    }
    set_state(DEVICE_SESSION_CALLING, DEVICE_SERVICE_CALL);
    s_session_deadline_ms = now_ms() + SESSION_REQUEST_TIMEOUT_MS;
    int rc = submit_service_event(EVENT_ACCEPT_RESPONSE,
                                  PLATFORM_SERVICE_CALL,
                                  "/v1/call/device/info",
                                  body);
    free(body);
    if (rc != 0) {
        ESP_LOGE(TAG, "device accept request submission failed rc=%d", rc);
        finish_session();
    }
}

static void handle_accept_response(const char *body)
{
    cJSON *root = NULL;
    const cJSON *data = NULL;
    char token[SESSION_ARGUMENT_MAX];
    bool ok = response_data(body, &root, &data) && cJSON_IsObject(data) &&
              copy_json_string(data, "token", token, sizeof(token));
    cJSON_Delete(root);
    if (!ok || s_call_peer_id[0] == '\0') {
        ESP_LOGE(TAG, "device accept response has no connection token");
        finish_session();
        return;
    }
    int rc = tirtc_adapter_connect(s_call_peer_id,
                                   token,
                                   s_session_generation);
    if (rc != 0) {
        ESP_LOGE(TAG, "device call P2P connection submission failed rc=%d", rc);
        finish_session();
    } else {
        s_session_deadline_ms = now_ms() + SESSION_CONNECT_TIMEOUT_MS;
    }
}

static const char *platform_audio_codec(device_audio_codec_t codec)
{
    switch (codec) {
    case DEVICE_AUDIO_CODEC_ALAW: return "alaw";
    case DEVICE_AUDIO_CODEC_AMR_NB:
    case DEVICE_AUDIO_CODEC_AMR_WB: return "amr";
    case DEVICE_AUDIO_CODEC_OPUS: return "opus";
    default: return "alaw";
    }
}

static void voip_profile_response(const char *body, void *user_data)
{
    (void)user_data;
    cJSON *root = body == NULL ? NULL : cJSON_Parse(body);
    const cJSON *code = root == NULL
                            ? NULL
                            : cJSON_GetObjectItemCaseSensitive(root, "code");
    bool accepted = cJSON_IsNumber(code) &&
                    (code->valueint == 0 || code->valueint == 200);
    cJSON_Delete(root);

    atomic_store_explicit(&s_voip_profile_pending, false, memory_order_release);
    atomic_store_explicit(&s_voip_profile_submitted,
                          accepted,
                          memory_order_release);
    if (accepted) {
        atomic_store_explicit(&s_voip_profile_retry_at_ms, 0, memory_order_release);
        ESP_LOGI(TAG, "VoIP audio-only profile accepted");
    } else {
        atomic_store_explicit(&s_voip_profile_retry_at_ms,
                              now_ms() + VOIP_PROFILE_RETRY_MS,
                              memory_order_release);
        ESP_LOGW(TAG, "VoIP profile failed; retrying in %u ms",
                 VOIP_PROFILE_RETRY_MS);
    }
}

static void submit_voip_profile(void)
{
    const device_media_config_t *media = media_runtime_config();
    if (media == NULL || !platform_client_ready()) {
        return;
    }
    if (atomic_load_explicit(&s_voip_profile_submitted, memory_order_acquire) ||
        atomic_load_explicit(&s_voip_profile_pending, memory_order_acquire) ||
        now_ms() < atomic_load_explicit(&s_voip_profile_retry_at_ms,
                                        memory_order_acquire)) {
        return;
    }
    atomic_store_explicit(&s_voip_profile_pending, true, memory_order_release);

    cJSON *root = cJSON_CreateObject();
    cJSON *profiles = root == NULL
                          ? NULL
                          : cJSON_AddObjectToObject(root, "profiles");
    cJSON *voip = profiles == NULL
                      ? NULL
                      : cJSON_AddObjectToObject(profiles, "voip");
    const bool no_video = true;
    const int screen_width = 1;
    const int screen_height = 1;
    const char *up_video_mt = "";
    const char *down_video_mt = "";
    bool ok = root != NULL && profiles != NULL && voip != NULL &&
              cJSON_AddNumberToObject(voip, "screen_width", screen_width) &&
              cJSON_AddNumberToObject(voip, "screen_height", screen_height) &&
              cJSON_AddNumberToObject(voip, "camera_rotation",
                                     media->video.camera_rotation) &&
              (!media->video.downlink_enabled ||
               media->video.down_video_rotation == 0 ||
               cJSON_AddNumberToObject(voip, "down_video_rotation",
                                      media->video.down_video_rotation)) &&
              cJSON_AddNumberToObject(voip, "aspect_ratio",
                                     media->video.aspect_ratio) &&
              (media->video.object_fit[0] == '\0' ||
               cJSON_AddStringToObject(voip, "object_fit",
                                      media->video.object_fit)) &&
              cJSON_AddBoolToObject(voip, "hor_mirror",
                                   media->video.hor_mirror) &&
              cJSON_AddBoolToObject(voip, "vert_mirror",
                                   media->video.vert_mirror) &&
              cJSON_AddNumberToObject(voip, "audio_rate", media->audio.sample_rate_hz) &&
              cJSON_AddNumberToObject(voip, "audio_channels", media->audio.channels) &&
              cJSON_AddStringToObject(voip, "up_video_mt", "none") &&
              cJSON_AddStringToObject(voip, "down_video_mt", "none") &&
              cJSON_AddStringToObject(voip, "down_audio_mt",
                                     platform_audio_codec(media->audio.codec)) &&
              cJSON_AddBoolToObject(voip, "no_video", no_video) &&
              cJSON_AddNumberToObject(voip, "calling_timeout_sec", 30);
    char *body = ok ? cJSON_PrintUnformatted(root) : NULL;
    cJSON_Delete(root);
    if (body == NULL) {
        atomic_store_explicit(&s_voip_profile_pending, false, memory_order_release);
        atomic_store_explicit(&s_voip_profile_retry_at_ms,
                              now_ms() + VOIP_PROFILE_RETRY_MS,
                              memory_order_release);
        ESP_LOGW(TAG, "cannot build VoIP device profile");
        return;
    }
    ESP_LOGI(TAG,
             "submitting VoIP profile screen=%dx%d audio=%s/%d/%d "
             "up-video=%s down-video=%s no-video=%s",
             screen_width,
             screen_height,
             platform_audio_codec(media->audio.codec),
             media->audio.sample_rate_hz,
             media->audio.channels,
             up_video_mt[0] == '\0' ? "none" : up_video_mt,
             down_video_mt[0] == '\0' ? "none" : down_video_mt,
             no_video ? "yes" : "no");
    esp_err_t err = platform_client_request(PLATFORM_SERVICE_DEVICE,
                                            "/v1/device/profile",
                                            body,
                                            voip_profile_response,
                                            NULL);
    free(body);
    if (err != ESP_OK) {
        atomic_store_explicit(&s_voip_profile_pending, false, memory_order_release);
        atomic_store_explicit(&s_voip_profile_retry_at_ms,
                              now_ms() + VOIP_PROFILE_RETRY_MS,
                              memory_order_release);
        ESP_LOGW(TAG, "VoIP profile submission failed: %s", esp_err_to_name(err));
    }
}

static void request_voip_callers(void)
{
    if (!atomic_load_explicit(&s_voip_profile_submitted, memory_order_acquire)) {
        submit_voip_profile();
    }
    if (submit_service_event(EVENT_VOIP_CALLERS_RESPONSE,
                             PLATFORM_SERVICE_VOIP,
                             "/v1/voip/device/contacts",
                             NULL) != ESP_OK) {
        ESP_LOGE(TAG, "VoIP caller list request submission failed");
        finish_session();
    }
}

static void handle_voip_callers_response(const char *body)
{
    if (s_state != DEVICE_SESSION_CALLING || s_service != DEVICE_SERVICE_VOIP) {
        return;
    }
    cJSON *root = NULL;
    const cJSON *data = NULL;
    if (!response_data(body, &root, &data) || !cJSON_IsObject(data)) {
        ESP_LOGE(TAG, "VoIP caller list response is invalid");
        finish_session();
        return;
    }
    const cJSON *list = cJSON_GetObjectItemCaseSensitive(data, "contacts");
    const cJSON *caller = cJSON_IsArray(list) ? cJSON_GetArrayItem(list, 0) : NULL;
    char app_id[65];
    char model_id[65];
    char open_id[129];
    bool ok = cJSON_IsObject(caller) &&
              copy_json_string(caller, "wx_app_id", app_id, sizeof(app_id)) &&
              copy_json_string(caller, "wx_model_id", model_id, sizeof(model_id)) &&
              copy_json_string(caller, "wx_open_id", open_id, sizeof(open_id));
    cJSON_Delete(root);
    if (!ok) {
        ESP_LOGW(TAG, "there is no usable authorized VoIP contact");
        finish_session();
        return;
    }

    runtime_tirtc_config_t runtime;
    if (runtime_config_load_tirtc(&runtime) != ESP_OK) {
        finish_session();
        return;
    }
    cJSON *request = cJSON_CreateObject();
    ok = request != NULL &&
         cJSON_AddStringToObject(request, "device_id", runtime.device_id) &&
         cJSON_AddStringToObject(request, "wx_app_id", app_id) &&
         cJSON_AddStringToObject(request, "wx_user_openid", open_id) &&
         cJSON_AddStringToObject(request, "wx_model_id", model_id) &&
         cJSON_AddStringToObject(request, "wx_room_type", "voice") &&
         cJSON_AddNumberToObject(request, "wx_version_type", 0);
    char *request_body = ok ? cJSON_PrintUnformatted(request) : NULL;
    cJSON_Delete(request);
    if (request_body == NULL) {
        finish_session();
        return;
    }
    s_voip_call_id[0] = '\0';
    s_voip_cancelled_open_id[0] = '\0';
    s_voip_cancelled_call_id[0] = '\0';
    s_voip_cancelled_until_ms = 0;
    (void)snprintf(s_voip_open_id, sizeof(s_voip_open_id), "%s", open_id);
    esp_err_t err = submit_service_event(EVENT_VOIP_DIAL_RESPONSE,
                                         PLATFORM_SERVICE_VOIP,
                                         "/v1/voip/device/call",
                                         request_body);
    free(request_body);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "VoIP dial request submission failed: %s", esp_err_to_name(err));
        finish_session();
    }
}

static void handle_voip_dial_response(const char *body)
{
    if (s_state != DEVICE_SESSION_CALLING || s_service != DEVICE_SERVICE_VOIP) {
        return;
    }
    cJSON *root = NULL;
    const cJSON *data = NULL;
    bool ok = response_data(body, &root, &data);
    if (ok && cJSON_IsObject(data)) {
        copy_optional_json_string(data,
                                  "call_id",
                                  s_voip_call_id,
                                  sizeof(s_voip_call_id));
    }
    cJSON_Delete(root);
    if (!ok) {
        if (s_voip_connect_submitted) {
            ESP_LOGW(TAG,
                     "ignoring failed VoIP dial response because WHIP setup is already in progress");
            return;
        }
        cJSON *error_root = body == NULL ? NULL : cJSON_Parse(body);
        const cJSON *code = error_root == NULL ? NULL :
            cJSON_GetObjectItemCaseSensitive(error_root, "code");
        if (cJSON_IsNumber(code) && code->valueint == 40205) {
            ESP_LOGW(TAG, "微信 VoIP 授权已失效，请让用户重新授权");
        } else if (cJSON_IsNumber(code) && code->valueint == 6006) {
            ESP_LOGW(TAG, "设备已解绑，请重新完成设备绑定");
        } else if (cJSON_IsNumber(code) && code->valueint == 401) {
            ESP_LOGW(TAG, "设备登录凭证无效或已过期，请重新获取 mqtt_token");
        } else {
            ESP_LOGE(TAG, "VoIP dial request was rejected");
        }
        cJSON_Delete(error_root);
        finish_session();
        return;
    }
    if (!s_voip_connect_submitted) {
        s_session_deadline_ms = now_ms() + SESSION_CALLING_TIMEOUT_MS;
    }
    ESP_LOGI(TAG, "VoIP calling first authorized contact; cancel after 30 seconds if unanswered");
}

static void handle_ai_token(const char *body)
{
    if (s_state != DEVICE_SESSION_AI_CONNECTING) {
        return;
    }
    if (body == NULL || body[0] == '\0') {
        ESP_LOGE(TAG, "AI token request returned no response; ending session");
        finish_session();
        return;
    }
    cJSON *root = cJSON_Parse(body);
    const cJSON *code = root == NULL ? NULL : cJSON_GetObjectItemCaseSensitive(root, "code");
    const cJSON *data = root == NULL ? NULL : cJSON_GetObjectItemCaseSensitive(root, "data");
    char peer_id[SESSION_ARGUMENT_MAX];
    char token[SESSION_ARGUMENT_MAX];
    bool code_ok = cJSON_IsNumber(code) && (code->valueint == 0 || code->valueint == 200);
    bool ok = code_ok && cJSON_IsObject(data) &&
              copy_json_string(data, "peer_id", peer_id, sizeof(peer_id)) &&
              copy_json_string(data, "token", token, sizeof(token));
    if (ok) {
        const cJSON *role = cJSON_GetObjectItemCaseSensitive(data, "role_id");
        if (cJSON_IsString(role) && role->valuestring != NULL) {
            (void)snprintf(s_ai_role_id, sizeof(s_ai_role_id), "%.64s", role->valuestring);
        } else {
            s_ai_role_id[0] = '\0';
        }
    }
    cJSON_Delete(root);

    if (!ok) {
        ESP_LOGE(TAG, "AI token response is invalid");
        finish_session();
        return;
    }
    int rc = tirtc_adapter_whip_connect(peer_id,
                                        token,
                                        s_session_generation);
    if (rc != 0) {
        ESP_LOGE(TAG, "AI WHIP connect submission failed rc=%d", rc);
        finish_session();
    } else {
        s_session_deadline_ms = now_ms() + SESSION_CONNECT_TIMEOUT_MS;
    }
}

static void send_ai_start(void)
{
    runtime_tirtc_config_t runtime;
    const device_media_config_t *media = media_runtime_config();
    if (runtime_config_load_tirtc(&runtime) != ESP_OK || media == NULL ||
        s_state != DEVICE_SESSION_AI_CONNECTING || !tirtc_adapter_has_connection()) {
        finish_session();
        return;
    }

    char request_id[17];
    (void)snprintf(request_id, sizeof(request_id), "%08lx%08lx",
                   (unsigned long)esp_random(), (unsigned long)esp_random());
    cJSON *root = cJSON_CreateObject();
    cJSON *params = cJSON_CreateObject();
    cJSON *input_audio = cJSON_CreateObject();
    cJSON *output_audio = cJSON_CreateObject();
    bool ok = root != NULL && params != NULL && input_audio != NULL && output_audio != NULL &&
              cJSON_AddStringToObject(root, "jsonrpc", "2.0") &&
              cJSON_AddStringToObject(root, "id", request_id) &&
              cJSON_AddStringToObject(root, "method", "start_session") &&
              cJSON_AddStringToObject(params, "device_id", runtime.device_id) &&
              cJSON_AddStringToObject(params, "role_id", s_ai_role_id) &&
              cJSON_AddStringToObject(input_audio, "codec",
                                      platform_audio_codec(media->audio.codec)) &&
              cJSON_AddNumberToObject(input_audio, "sample_rate", media->audio.sample_rate_hz) &&
              cJSON_AddNumberToObject(input_audio, "channels", media->audio.channels) &&
              cJSON_AddStringToObject(output_audio, "codec",
                                      platform_audio_codec(media->audio.codec)) &&
              cJSON_AddNumberToObject(output_audio, "sample_rate", media->audio.sample_rate_hz) &&
              cJSON_AddNumberToObject(output_audio, "channels", media->audio.channels);
    if (ok) {
        cJSON_AddItemToObject(params, "input_audio", input_audio);
        input_audio = NULL;
        cJSON_AddItemToObject(params, "output_audio", output_audio);
        output_audio = NULL;
        cJSON_AddItemToObject(root, "params", params);
        params = NULL;
    }
    char *json = ok ? cJSON_PrintUnformatted(root) : NULL;
    cJSON_Delete(input_audio);
    cJSON_Delete(output_audio);
    cJSON_Delete(params);
    cJSON_Delete(root);
    if (json == NULL) {
        ESP_LOGE(TAG, "cannot build AI start_session command");
        finish_session();
        return;
    }
    int rc = tirtc_adapter_send_command(CMD_AI, json, strlen(json));
    free(json);
    s_ai_start_at_ms = 0;
    if (rc < 0) {
        ESP_LOGE(TAG, "AI start_session send failed rc=%d", rc);
        finish_session();
    } else {
        s_session_deadline_ms = now_ms() + SESSION_AI_RESPONSE_TIMEOUT_MS;
        ESP_LOGI(TAG, "AI start_session sent; waiting for response");
    }
}

static void handle_connection(const session_event_t *event)
{
    if (!event->connected) {
        if (event->connection_generation != 0 &&
            event->connection_generation != s_bound_connection_generation) {
            ESP_LOGI(TAG,
                     "ignoring stale disconnect generation=%lu active=%lu",
                     (unsigned long)event->connection_generation,
                     (unsigned long)s_bound_connection_generation);
            return;
        }
        s_bound_connection_generation = 0;
        media_runtime_set_uplink_active(false);
        if (s_service == DEVICE_SERVICE_CALL && s_call_room_id[0] != '\0' &&
            (s_state == DEVICE_SESSION_CALLING || s_state == DEVICE_SESSION_IN_CALL)) {
            (void)submit_room_action("/v1/call/hangup", "connection_error");
        }
        if (s_state != DEVICE_SESSION_IDLE && s_state != DEVICE_SESSION_OFFLINE) {
            finish_session();
        }
        return;
    }

    /*
     * The target is audio-only for every service. Rejecting
     * on_subscribe_video protects our uplink; this explicit unsubscribe is
     * the independent downlink direction and asks the peer to stop stream 11.
     */
    (void)tirtc_adapter_disable_video_downlink();

    if (event->incoming) {
        if (s_state == DEVICE_SESSION_IDLE) {
            begin_session(DEVICE_SESSION_H5_STREAMING, DEVICE_SERVICE_H5);
            s_bound_connection_generation = event->connection_generation;
            media_runtime_set_uplink_active(true);
        } else if (s_state == DEVICE_SESSION_RINGING) {
            ESP_LOGW(TAG,
                     "rejecting media connection while ringing; accept signaling first");
            (void)tirtc_adapter_disconnect();
        } else if (s_state == DEVICE_SESSION_CALLING &&
                   s_service == DEVICE_SERVICE_CALL) {
            s_bound_connection_generation = event->connection_generation;
            ESP_LOGI(TAG, "callee P2P connected; waiting for room confirmation command");
        } else {
            ESP_LOGW(TAG, "unexpected incoming connection while %s; closing",
                     device_session_state_name(s_state));
            (void)tirtc_adapter_disconnect();
        }
        return;
    }

    s_bound_connection_generation = event->connection_generation;
    if (s_service == DEVICE_SERVICE_AI && s_state == DEVICE_SESSION_AI_CONNECTING) {
        s_ai_start_at_ms = esp_timer_get_time() / 1000 + 300;
        s_session_deadline_ms = now_ms() + SESSION_AI_RESPONSE_TIMEOUT_MS;
    } else if (s_service == DEVICE_SERVICE_VOIP &&
               s_state == DEVICE_SESSION_CALLING) {
        s_session_deadline_ms = now_ms() + SESSION_CONFIRM_TIMEOUT_MS;
        ESP_LOGI(TAG,
                 "VoIP WHIP connected; waiting for 0x2000 confirmation");
    } else if (s_service == DEVICE_SERVICE_CALL &&
               s_state == DEVICE_SESSION_CALLING) {
        set_state(DEVICE_SESSION_IN_CALL, s_service);
        s_session_deadline_ms = 0;
        media_runtime_set_uplink_active(true);
        char room[192];
        int length = snprintf(room,
                              sizeof(room),
                              "{\"room_id\":\"%s\"}",
                              s_call_room_id[0] == '\0' ? "direct-demo" : s_call_room_id);
        if (length > 0 && (size_t)length < sizeof(room)) {
            (void)tirtc_adapter_send_command(CMD_VOIP_ACCEPT,
                                             room,
                                             (uint32_t)length);
        }
    } else {
        ESP_LOGW(TAG, "outgoing connection completed after its session ended; closing");
        (void)tirtc_adapter_disconnect();
    }
}

static void handle_command(const session_event_t *event)
{
    if (event->connection_generation == 0 ||
        event->connection_generation != s_bound_connection_generation) {
        ESP_LOGI(TAG,
                 "ignoring stale command=0x%lx generation=%lu active=%lu",
                 (unsigned long)event->command,
                 (unsigned long)event->connection_generation,
                 (unsigned long)s_bound_connection_generation);
        return;
    }
    if (event->command == CMD_AI && s_service == DEVICE_SERVICE_AI) {
        cJSON *root = cJSON_ParseWithLength(event->payload, event->length);
        bool error = root != NULL && cJSON_GetObjectItemCaseSensitive(root, "error") != NULL;
        bool response = root != NULL &&
                        cJSON_GetObjectItemCaseSensitive(root, "result") != NULL;
        cJSON_Delete(root);
        if (error) {
            ESP_LOGE(TAG, "AI start_session was rejected");
            finish_session();
        } else if (response && s_state == DEVICE_SESSION_AI_CONNECTING) {
            set_state(DEVICE_SESSION_AI_ACTIVE, DEVICE_SERVICE_AI);
            s_session_deadline_ms = 0;
            media_runtime_set_uplink_active(true);
        }
    } else if (event->command == CMD_VOIP_HANGUP) {
        ESP_LOGI(TAG, "remote hangup received");
        finish_session();
    } else if (event->command == CMD_VOIP_ACCEPT &&
               (s_service == DEVICE_SERVICE_VOIP || s_service == DEVICE_SERVICE_CALL)) {
        if (s_service == DEVICE_SERVICE_CALL && s_call_room_id[0] != '\0') {
            cJSON *root = cJSON_ParseWithLength(event->payload, event->length);
            const cJSON *room = root == NULL
                                    ? NULL
                                    : cJSON_GetObjectItemCaseSensitive(root, "room_id");
            bool matches = cJSON_IsString(room) && room->valuestring != NULL &&
                           strcmp(room->valuestring, s_call_room_id) == 0;
            cJSON_Delete(root);
            if (!matches) {
                ESP_LOGW(TAG, "ignoring call confirmation for a different room");
                (void)tirtc_adapter_disconnect();
                return;
            }
        }
        s_session_deadline_ms = 0;
        set_state(DEVICE_SESSION_IN_CALL, s_service);
        media_runtime_set_uplink_active(true);
    }
}

static void handle_event(const session_event_t *event)
{
    if (event->session_generation != 0 &&
        event->session_generation != s_session_generation) {
        ESP_LOGI(TAG,
                 "ignoring stale event=%d session=%lu active=%lu",
                 (int)event->type,
                 (unsigned long)event->session_generation,
                 (unsigned long)s_session_generation);
        return;
    }

    switch (event->type) {
    case EVENT_CONNECTION:
        handle_connection(event);
        break;
    case EVENT_COMMAND:
        handle_command(event);
        break;
    case EVENT_PLATFORM_SIGNAL:
        handle_platform_signal(event);
        break;
    case EVENT_VOIP_CALL_DEFAULT:
        if (s_state != DEVICE_SESSION_IDLE && s_state != DEVICE_SESSION_H5_STREAMING) {
            ESP_LOGW(TAG, "VoIP call ignored while %s", device_session_state_name(s_state));
            break;
        }
        if (!platform_client_ready() ||
            tirtc_adapter_state() != TIRTC_ADAPTER_RUNNING) {
            ESP_LOGW(TAG,
                     "VoIP call unavailable: platform=%s TiRTC=%d",
                     platform_client_ready() ? "ready" : "offline",
                     (int)tirtc_adapter_state());
            break;
        }
        if (tirtc_adapter_has_connection()) {
            media_runtime_set_uplink_active(false);
            (void)tirtc_adapter_disconnect();
        }
        begin_session(DEVICE_SESSION_CALLING, DEVICE_SERVICE_VOIP);
        s_voip_outgoing = true;
        s_voip_connect_submitted = false;
        s_session_deadline_ms = now_ms() + SESSION_REQUEST_TIMEOUT_MS;
        request_voip_callers();
        break;
    case EVENT_VOIP_CALLERS_RESPONSE:
        handle_voip_callers_response(event->payload);
        break;
    case EVENT_VOIP_DIAL_RESPONSE:
        handle_voip_dial_response(event->payload);
        break;
    case EVENT_AI_TOKEN:
        handle_ai_token(event->payload);
        break;
    case EVENT_CONTACTS:
        request_contacts(false);
        break;
    case EVENT_CONTACTS_RESPONSE:
        handle_contacts_response(event->payload);
        break;
    case EVENT_CALL_REQUEST_RESPONSE:
        handle_call_request_response(event->payload);
        break;
    case EVENT_ROOM_RESPONSE:
        handle_room_response(event->payload);
        break;
    case EVENT_ACCEPT_RESPONSE:
        handle_accept_response(event->payload);
        break;
    case EVENT_AI_PRESS:
        if (s_state != DEVICE_SESSION_IDLE && s_state != DEVICE_SESSION_H5_STREAMING) {
            ESP_LOGW(TAG, "AI press ignored while %s", device_session_state_name(s_state));
            break;
        }
        if (!platform_client_ready() ||
            tirtc_adapter_state() != TIRTC_ADAPTER_RUNNING) {
            ESP_LOGW(TAG,
                     "AI unavailable: platform=%s TiRTC=%d",
                     platform_client_ready() ? "ready" : "offline",
                     (int)tirtc_adapter_state());
            break;
        }
        if (tirtc_adapter_has_connection()) {
            media_runtime_set_uplink_active(false);
            (void)tirtc_adapter_disconnect();
        }
        begin_session(DEVICE_SESSION_AI_CONNECTING, DEVICE_SERVICE_AI);
        s_session_deadline_ms = now_ms() + SESSION_REQUEST_TIMEOUT_MS;
        if (submit_service_event(EVENT_AI_TOKEN,
                                 PLATFORM_SERVICE_AI,
                                 "/v1/ai/token",
                                 NULL) != ESP_OK) {
            ESP_LOGE(TAG, "AI token request submission failed");
            finish_session();
        }
        break;
    case EVENT_AI_RELEASE:
        if (s_service == DEVICE_SERVICE_AI &&
            (s_state == DEVICE_SESSION_AI_CONNECTING ||
             s_state == DEVICE_SESSION_AI_ACTIVE)) {
            if (tirtc_adapter_has_connection()) {
                const char end[] = "{\"jsonrpc\":\"2.0\",\"method\":\"end_session\"}";
                (void)tirtc_adapter_send_command(CMD_AI, end, sizeof(end) - 1U);
            }
            finish_session();
        }
        break;
    case EVENT_VOIP_CONNECT:
    case EVENT_DEVICE_CALL:
        if (s_state != DEVICE_SESSION_IDLE && s_state != DEVICE_SESSION_H5_STREAMING) {
            ESP_LOGW(TAG, "call ignored while %s", device_session_state_name(s_state));
            break;
        }
        if (tirtc_adapter_state() != TIRTC_ADAPTER_RUNNING) {
            ESP_LOGW(TAG,
                     "direct connection unavailable before TiRTC is running");
            break;
        }
        if (tirtc_adapter_has_connection()) {
            media_runtime_set_uplink_active(false);
            (void)tirtc_adapter_disconnect();
        }
        device_service_t service = event->type == EVENT_VOIP_CONNECT
                                       ? DEVICE_SERVICE_VOIP
                                       : DEVICE_SERVICE_CALL;
        begin_session(DEVICE_SESSION_CALLING, service);
        s_call_outgoing = service == DEVICE_SERVICE_CALL;
        s_voip_outgoing = service == DEVICE_SERVICE_VOIP;
        s_voip_connect_submitted = false;
        int rc = event->type == EVENT_VOIP_CONNECT
                     ? tirtc_adapter_whip_connect(event->first,
                                                  event->second,
                                                  s_session_generation)
                     : tirtc_adapter_connect(event->first,
                                             event->second,
                                             s_session_generation);
        if (rc != 0) {
            ESP_LOGE(TAG, "call connection submission failed rc=%d", rc);
            finish_session();
        } else {
            s_voip_connect_submitted = service == DEVICE_SERVICE_VOIP;
            s_session_deadline_ms = now_ms() + SESSION_CONNECT_TIMEOUT_MS;
        }
        break;
    case EVENT_CALL_DEFAULT:
        if (s_state != DEVICE_SESSION_IDLE && s_state != DEVICE_SESSION_H5_STREAMING) {
            ESP_LOGW(TAG, "call ignored while %s", device_session_state_name(s_state));
            break;
        }
        request_contacts(true);
        break;
    case EVENT_CANCEL:
        if (s_state == DEVICE_SESSION_CALLING || s_state == DEVICE_SESSION_AI_CONNECTING) {
            if (s_service == DEVICE_SERVICE_CALL && s_call_room_id[0] != '\0') {
                (void)submit_room_action(s_call_outgoing
                                             ? "/v1/call/cancel"
                                             : "/v1/call/hangup",
                                         s_call_outgoing ? NULL : "cancelled");
            } else if (s_service == DEVICE_SERVICE_VOIP && s_voip_open_id[0] != '\0') {
                if (s_voip_outgoing) {
                    remember_cancelled_voip();
                } else {
                    reject_voip_signal(7);
                }
            }
            finish_session();
        } else {
            ESP_LOGW(TAG, "cancel ignored while %s",
                     device_session_state_name(s_state));
        }
        break;
    case EVENT_HANGUP:
        if (s_state == DEVICE_SESSION_IN_CALL || s_state == DEVICE_SESSION_AI_ACTIVE ||
            s_state == DEVICE_SESSION_H5_STREAMING) {
            if (s_service == DEVICE_SERVICE_AI) {
                const char end[] = "{\"jsonrpc\":\"2.0\",\"method\":\"end_session\"}";
                (void)tirtc_adapter_send_command(CMD_AI, end, sizeof(end) - 1U);
            } else if (s_service == DEVICE_SERVICE_VOIP) {
                const char hangup[] = "{\"reason\":0}";
                (void)tirtc_adapter_send_command(CMD_VOIP_HANGUP,
                                                  hangup,
                                                  sizeof(hangup) - 1U);
            } else if (s_service == DEVICE_SERVICE_CALL && s_call_room_id[0] != '\0') {
                (void)submit_room_action("/v1/call/hangup", "hangup");
            }
            finish_session();
        } else {
            ESP_LOGW(TAG, "hangup ignored while %s",
                     device_session_state_name(s_state));
        }
        break;
    case EVENT_ACCEPT:
        if (s_state == DEVICE_SESSION_RINGING) {
            if (tirtc_adapter_state() != TIRTC_ADAPTER_RUNNING) {
                ESP_LOGW(TAG,
                         "accept unavailable before TiRTC is running; call remains ringing");
                break;
            }
            if (s_service == DEVICE_SERVICE_CALL) {
                accept_device_call();
            } else if (s_service == DEVICE_SERVICE_VOIP) {
                set_state(DEVICE_SESSION_CALLING, DEVICE_SERVICE_VOIP);
                s_session_deadline_ms = now_ms() + SESSION_CONNECT_TIMEOUT_MS;
                if (tirtc_adapter_whip_connect(s_voip_peer_id,
                                               s_voip_token,
                                               s_session_generation) != 0) {
                    finish_session();
                } else {
                    s_voip_connect_submitted = true;
                }
            } else {
                set_state(DEVICE_SESSION_CALLING, s_service);
            }
        } else {
            ESP_LOGW(TAG, "accept ignored while %s",
                     device_session_state_name(s_state));
        }
        break;
    case EVENT_REJECT:
        if (s_state == DEVICE_SESSION_RINGING) {
            if (s_service == DEVICE_SERVICE_CALL && s_call_room_id[0] != '\0') {
                (void)submit_room_action("/v1/call/reject", "decline");
            } else if (s_service == DEVICE_SERVICE_VOIP) {
                reject_voip_signal(7);
            }
            finish_session();
        } else {
            ESP_LOGW(TAG, "reject ignored while %s",
                     device_session_state_name(s_state));
        }
        break;
    default:
        break;
    }
}

static void handle_session_deadline(void)
{
    const device_session_state_t expired_state = s_state;
    const device_service_t expired_service = s_service;
    s_session_deadline_ms = 0;

    if (expired_state == DEVICE_SESSION_RINGING) {
        if (expired_service == DEVICE_SERVICE_CALL &&
            s_call_room_id[0] != '\0') {
            ESP_LOGW(TAG,
                     "incoming device call timed out; rejecting room=%s",
                     s_call_room_id);
            (void)submit_room_action("/v1/call/reject", "timeout");
        } else if (expired_service == DEVICE_SERVICE_VOIP) {
            ESP_LOGW(TAG,
                     "incoming VoIP call timed out; rejecting room=%s",
                     s_voip_room_id);
            reject_voip_signal(7);
        }
        finish_session();
        return;
    }

    if (expired_state == DEVICE_SESSION_AI_CONNECTING) {
        ESP_LOGW(TAG, "AI session setup timed out");
        finish_session();
        return;
    }

    if (expired_state != DEVICE_SESSION_CALLING) {
        return;
    }

    if (expired_service == DEVICE_SERVICE_CALL) {
        ESP_LOGW(TAG,
                 "%s device call timed out room=%s",
                 s_call_outgoing ? "outgoing" : "incoming",
                 s_call_room_id);
        if (s_call_room_id[0] != '\0') {
            (void)submit_room_action(s_call_outgoing
                                         ? "/v1/call/cancel"
                                         : "/v1/call/hangup",
                                     s_call_outgoing
                                         ? NULL
                                         : "connection_timeout");
        }
    } else if (expired_service == DEVICE_SERVICE_VOIP) {
        ESP_LOGW(TAG,
                 "%s VoIP call setup timed out room=%s",
                 s_voip_outgoing ? "outgoing" : "incoming",
                 s_voip_room_id);
        if (s_voip_outgoing) {
            remember_cancelled_voip();
        } else {
            reject_voip_signal(7);
        }
    }
    finish_session();
}

static void session_task(void *argument)
{
    (void)argument;
    set_state(DEVICE_SESSION_IDLE, DEVICE_SERVICE_H5);
    s_next_room_poll_ms = now_ms() + 1000;
    for (;;) {
        session_event_t event = {0};
        if (xQueueReceive(s_queue, &event, pdMS_TO_TICKS(50)) == pdTRUE) {
            handle_event(&event);
            release_event(&event);
        }
        const int64_t current_ms = now_ms();
        if (s_ai_start_at_ms != 0 && current_ms >= s_ai_start_at_ms) {
            send_ai_start();
        }
        if (s_session_deadline_ms != 0 &&
            current_ms >= s_session_deadline_ms) {
            handle_session_deadline();
        }
        if (!atomic_load_explicit(&s_voip_profile_submitted,
                                  memory_order_acquire) &&
            platform_client_ready()) {
            submit_voip_profile();
        }
        const bool room_poll_allowed =
            platform_client_ready() &&
            !platform_client_mqtt_connected() &&
            tirtc_adapter_state() == TIRTC_ADAPTER_RUNNING &&
            s_service != DEVICE_SERVICE_AI && s_service != DEVICE_SERVICE_VOIP;
        if (room_poll_allowed &&
            !atomic_load_explicit(&s_room_request_pending, memory_order_acquire) &&
            current_ms >= s_next_room_poll_ms) {
            atomic_store_explicit(&s_room_request_pending,
                                  true,
                                  memory_order_release);
            s_next_room_poll_ms = current_ms + 2000;
            if (submit_service_event_timeout(EVENT_ROOM_RESPONSE,
                                             PLATFORM_SERVICE_CALL,
                                             "/v1/call/room",
                                             NULL,
                                             2500U) != ESP_OK) {
                atomic_store_explicit(&s_room_request_pending,
                                      false,
                                      memory_order_release);
                ESP_LOGW(TAG, "room status request submission failed");
            }
        }
    }
}

static esp_err_t enqueue_simple(session_event_type_t type)
{
    const session_event_t event = {
        .type = type,
    };
    bool queued = queue_event(&event);
    return queued ? ESP_OK : ESP_ERR_TIMEOUT;
}

static esp_err_t enqueue_pair(session_event_type_t type, const char *first, const char *second)
{
    if (first == NULL || first[0] == '\0' || second == NULL || second[0] == '\0' ||
        strlen(first) >= SESSION_ARGUMENT_MAX || strlen(second) >= SESSION_ARGUMENT_MAX) {
        return ESP_ERR_INVALID_ARG;
    }
    session_event_t event = {
        .type = type,
    };
    if (!copy_event_text(&event.first,
                         NULL,
                         first,
                         strlen(first),
                         SESSION_ARGUMENT_MAX) ||
        !copy_event_text(&event.second,
                         NULL,
                         second,
                         strlen(second),
                         SESSION_ARGUMENT_MAX)) {
        release_event(&event);
        return ESP_ERR_NO_MEM;
    }
    bool queued = queue_event(&event);
    if (!queued) {
        release_event(&event);
    }
    return queued ? ESP_OK : ESP_ERR_TIMEOUT;
}

esp_err_t session_runtime_start(void)
{
    if (s_task != NULL) {
        return ESP_OK;
    }
    s_queue = xQueueCreate(SESSION_QUEUE_DEPTH, sizeof(session_event_t));
    if (s_queue == NULL) {
        return ESP_ERR_NO_MEM;
    }
    const tirtc_adapter_event_handlers_t handlers = {
        .on_connection_changed = adapter_connection_changed,
        .on_command = adapter_command,
    };
    tirtc_adapter_set_event_handlers(&handlers);
    platform_client_set_signal_handler(platform_signal, NULL);
    if (xTaskCreate(session_task, "session", 24576, NULL, 6, &s_task) != pdPASS) {
        vQueueDelete(s_queue);
        s_queue = NULL;
        return ESP_ERR_NO_MEM;
    }
    return ESP_OK;
}

device_session_state_t session_runtime_state(void)
{
    return s_state;
}

device_service_t session_runtime_service(void)
{
    return s_service;
}

esp_err_t session_runtime_ai_press(void) { return enqueue_simple(EVENT_AI_PRESS); }
esp_err_t session_runtime_ai_release(void) { return enqueue_simple(EVENT_AI_RELEASE); }
esp_err_t session_runtime_voip_call_default(void)
{
    return enqueue_simple(EVENT_VOIP_CALL_DEFAULT);
}
esp_err_t session_runtime_voip_connect(const char *peer, const char *token)
{
    return enqueue_pair(EVENT_VOIP_CONNECT, peer, token);
}
esp_err_t session_runtime_contacts(void) { return enqueue_simple(EVENT_CONTACTS); }
esp_err_t session_runtime_device_call_default(void)
{
    return enqueue_simple(EVENT_CALL_DEFAULT);
}
esp_err_t session_runtime_device_call(const char *remote, const char *token)
{
    return enqueue_pair(EVENT_DEVICE_CALL, remote, token);
}
esp_err_t session_runtime_accept(void) { return enqueue_simple(EVENT_ACCEPT); }
esp_err_t session_runtime_reject(void) { return enqueue_simple(EVENT_REJECT); }
esp_err_t session_runtime_cancel(void) { return enqueue_simple(EVENT_CANCEL); }
esp_err_t session_runtime_hangup(void) { return enqueue_simple(EVENT_HANGUP); }

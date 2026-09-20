#include "tirtc_adapter.h"

#include <stddef.h>
#include <stdatomic.h>
#include <stdint.h>
#include <string.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "tirtc/tiRTC.h"

#ifndef TIRTC_SDK_STATIC_SEMAPHORE_SIZE
#error "TiRTC SDK build contract did not define StaticSemaphore_t size"
#endif

_Static_assert(sizeof(StaticSemaphore_t) == TIRTC_SDK_STATIC_SEMAPHORE_SIZE,
               "FreeRTOS StaticSemaphore_t does not match the TiRTC SDK build contract");

static const char *TAG = "tirtc_adapter";
static volatile tirtc_adapter_state_t s_state = TIRTC_ADAPTER_IDLE;
static bool s_initialized;
static atomic_uint_fast32_t s_audio_rx_frames;
static atomic_uint_fast32_t s_video_rx_frames;
static atomic_uintptr_t s_active_connection;
static atomic_uint_fast32_t s_connection_generation;
static atomic_uint_fast32_t s_active_connection_generation;
static atomic_uint_fast32_t s_active_connection_request_tag;
static atomic_bool s_connection_incoming;
static atomic_uint_fast32_t s_connect_request_generation;
static atomic_uint_fast32_t s_connect_request_tag;
static atomic_bool s_connect_request_pending;
static atomic_bool s_audio_subscribed;
static tirtc_adapter_event_handlers_t s_event_handlers;

#define STREAM_ID_AUDIO 10U
#define STREAM_ID_VIDEO 11U

static void clear_media_subscriptions(void)
{
    atomic_store_explicit(&s_audio_subscribed, false, memory_order_release);
}

static bool is_active_connection(tirtc_conn_t connection)
{
    return atomic_load_explicit(&s_active_connection, memory_order_acquire) ==
           (uintptr_t)connection;
}

static uint32_t next_connection_generation(void)
{
    return (uint32_t)atomic_fetch_add_explicit(
               &s_connection_generation, 1, memory_order_acq_rel) +
           1U;
}

static void notify_connection_changed(bool connected,
                                      bool incoming,
                                      uint32_t connection_generation,
                                      uint32_t request_tag)
{
    if (s_event_handlers.on_connection_changed != NULL) {
        s_event_handlers.on_connection_changed(connected,
                                               incoming,
                                               connection_generation,
                                               request_tag,
                                               s_event_handlers.user_data);
    }
}

static const char *media_name(uint8_t media)
{
    switch (media) {
    case TIRTC_AUDIO_PCM: return "pcm";
    case TIRTC_AUDIO_ALAW: return "alaw";
    case TIRTC_AUDIO_AAC: return "aac";
    case TIRTC_AUDIO_OPUS: return "opus";
    case TIRTC_AUDIO_AMR: return "amr";
    case TIRTC_VIDEO_JPEG: return "mjpeg";
    case TIRTC_VIDEO_H264: return "h264";
    case TIRTC_VIDEO_H265: return "h265";
    default: return "unknown";
    }
}

static void sdk_log(const char *log, uint32_t length)
{
    if (log != NULL && length > 0) {
        ESP_LOGI("TiRTC", "%.*s", (int)length, log);
    }
}

static void on_event(int event, const void *data, int len)
{
    (void)data;
    (void)len;

    switch (event) {
    case TIRTC_EVENT_SYS_STARTED:
        s_state = TIRTC_ADAPTER_RUNNING;
        ESP_LOGI(TAG, "SDK started");
        break;
    case TIRTC_EVENT_SYS_STOPPED:
        s_state = TIRTC_ADAPTER_STOPPED;
        ESP_LOGI(TAG, "SDK stopped");
        break;
    default:
        ESP_LOGI(TAG, "SDK event=%d", event);
        break;
    }
}

static void on_conn_accepted(tirtc_conn_t connection)
{
    uintptr_t expected = 0;
    if (!atomic_compare_exchange_strong_explicit(&s_active_connection,
                                                  &expected,
                                                  (uintptr_t)connection,
                                                  memory_order_acq_rel,
                                                  memory_order_acquire)) {
        ESP_LOGW(TAG, "rejecting additional connection while another session is active");
        (void)TiRtcDisconnect(connection);
        return;
    }
    clear_media_subscriptions();
    atomic_store_explicit(&s_connection_incoming, true, memory_order_release);
    uint32_t generation = next_connection_generation();
    atomic_store_explicit(&s_active_connection_generation,
                          generation,
                          memory_order_release);
    atomic_store_explicit(&s_active_connection_request_tag, 0, memory_order_release);
    ESP_LOGI(TAG, "incoming connection accepted handle=%p", (void *)connection);
    notify_connection_changed(true, true, generation, 0);
}

static void on_conn_error(tirtc_conn_t connection, int error)
{
    ESP_LOGW(TAG, "connection error=%d (%s)", error, TiRtcGetErrorStr(error));
    uintptr_t expected = (uintptr_t)connection;
    if (atomic_compare_exchange_strong_explicit(&s_active_connection,
                                                &expected,
                                                0,
                                                memory_order_acq_rel,
                                                memory_order_acquire)) {
        uint32_t generation = (uint32_t)atomic_exchange_explicit(
            &s_active_connection_generation, 0, memory_order_acq_rel);
        uint32_t request_tag = (uint32_t)atomic_exchange_explicit(
            &s_active_connection_request_tag, 0, memory_order_acq_rel);
        clear_media_subscriptions();
        bool incoming =
            atomic_load_explicit(&s_connection_incoming, memory_order_acquire);
        notify_connection_changed(false, incoming, generation, request_tag);
    }
    if (connection != NULL) {
        (void)TiRtcDisconnect(connection);
    }
}

static void on_disconnected(tirtc_conn_t connection)
{
    uintptr_t expected = (uintptr_t)connection;
    if (atomic_compare_exchange_strong_explicit(&s_active_connection,
                                                &expected,
                                                0,
                                                memory_order_acq_rel,
                                                memory_order_acquire)) {
        uint32_t generation = (uint32_t)atomic_exchange_explicit(
            &s_active_connection_generation, 0, memory_order_acq_rel);
        uint32_t request_tag = (uint32_t)atomic_exchange_explicit(
            &s_active_connection_request_tag, 0, memory_order_acq_rel);
        clear_media_subscriptions();
        bool incoming =
            atomic_load_explicit(&s_connection_incoming, memory_order_acquire);
        notify_connection_changed(false, incoming, generation, request_tag);
    }
    ESP_LOGI(TAG, "connection disconnected handle=%p", (void *)connection);
}

static void on_connect_result(int error, tirtc_conn_t connection, void *user_data)
{
    uint32_t request_generation = (uint32_t)(uintptr_t)user_data;
    bool current_request =
        request_generation != 0 &&
        request_generation ==
            atomic_load_explicit(&s_connect_request_generation, memory_order_acquire) &&
        atomic_load_explicit(&s_connect_request_pending, memory_order_acquire);
    if (!current_request) {
        if (error == 0 && connection != NULL) {
            ESP_LOGI(TAG, "closing stale outgoing connection handle=%p", (void *)connection);
            (void)TiRtcDisconnect(connection);
        }
        return;
    }

    if (error != 0 || connection == NULL) {
        atomic_store_explicit(&s_connect_request_pending, false, memory_order_release);
        uint32_t request_tag = (uint32_t)atomic_load_explicit(
            &s_connect_request_tag, memory_order_acquire);
        ESP_LOGE(TAG, "outgoing connection failed: %d (%s)", error, TiRtcGetErrorStr(error));
        notify_connection_changed(false, false, 0, request_tag);
        return;
    }

    uintptr_t expected = 0;
    if (!atomic_compare_exchange_strong_explicit(&s_active_connection,
                                                  &expected,
                                                  (uintptr_t)connection,
                                                  memory_order_acq_rel,
                                                  memory_order_acquire)) {
        ESP_LOGW(TAG, "outgoing connection completed after another session became active; closing it");
        atomic_store_explicit(&s_connect_request_pending, false, memory_order_release);
        (void)TiRtcDisconnect(connection);
        return;
    }
    if (request_generation !=
        atomic_load_explicit(&s_connect_request_generation, memory_order_acquire)) {
        uintptr_t expected_connection = (uintptr_t)connection;
        (void)atomic_compare_exchange_strong_explicit(&s_active_connection,
                                                       &expected_connection,
                                                       0,
                                                       memory_order_acq_rel,
                                                       memory_order_acquire);
        atomic_store_explicit(&s_connect_request_pending, false, memory_order_release);
        ESP_LOGI(TAG, "outgoing connection was cancelled before completion; closing it");
        (void)TiRtcDisconnect(connection);
        return;
    }
    atomic_store_explicit(&s_connect_request_pending, false, memory_order_release);
    clear_media_subscriptions();
    atomic_store_explicit(&s_connection_incoming, false, memory_order_release);
    uint32_t generation = next_connection_generation();
    uint32_t request_tag = (uint32_t)atomic_load_explicit(
        &s_connect_request_tag, memory_order_acquire);
    atomic_store_explicit(&s_active_connection_generation,
                          generation,
                          memory_order_release);
    atomic_store_explicit(&s_active_connection_request_tag,
                          request_tag,
                          memory_order_release);
    ESP_LOGI(TAG, "outgoing connection established handle=%p", (void *)connection);
    notify_connection_changed(true, false, generation, request_tag);
}

static void on_command(tirtc_conn_t connection,
                       uint32_t command,
                       const void *data,
                       uint32_t length)
{
    if (is_active_connection(connection) &&
        s_event_handlers.on_command != NULL) {
        uint32_t generation = (uint32_t)atomic_load_explicit(
            &s_active_connection_generation, memory_order_acquire);
        s_event_handlers.on_command(command,
                                    data,
                                    length,
                                    generation,
                                    s_event_handlers.user_data);
    }
}

static void on_request_key_frame(tirtc_conn_t connection, uint8_t stream_id)
{
    (void)connection;
    ESP_LOGI(TAG, "key-frame requested stream=%u", stream_id);
}

static int on_subscribe_video(tirtc_conn_t connection, uint8_t stream_id)
{
    (void)connection;
    ESP_LOGI(TAG,
             "video subscription stream=%u rejected: ESP32-S3 target is audio-only",
             stream_id);
    return -1;
}

static int on_subscribe_audio(tirtc_conn_t connection, uint8_t stream_id)
{
    bool active = is_active_connection(connection);
    bool accepted = active && stream_id == STREAM_ID_AUDIO;
    if (active) {
        atomic_store_explicit(&s_audio_subscribed, accepted, memory_order_release);
    }
    ESP_LOGI(TAG, "audio subscription stream=%u %s",
             stream_id,
             accepted ? "accepted" : "rejected by stream id");
    return accepted ? 0 : -1;
}

static void on_unsubscribe(tirtc_conn_t connection, uint8_t stream_id)
{
    if (is_active_connection(connection)) {
        if (stream_id == STREAM_ID_AUDIO) {
            atomic_store_explicit(&s_audio_subscribed, false, memory_order_release);
        }
    }
    ESP_LOGI(TAG, "media unsubscribed stream=%u", stream_id);
}

static void on_audio(tirtc_conn_t connection, const TIRTCFRAMEINFO *frame, void *data)
{
    (void)data;
    if (frame == NULL || !is_active_connection(connection)) {
        return;
    }

    uint32_t count = (uint32_t)atomic_fetch_add_explicit(
                         &s_audio_rx_frames, 1, memory_order_relaxed) + 1U;
    if (count <= 3U || count % 500U == 0U) {
        ESP_LOGI(TAG,
                 "RX audio #%lu stream=%u codec=%s len=%lu ts=%lu; no speaker sink, dropped",
                 (unsigned long)count,
                 frame->stream_id,
                 media_name(frame->media),
                 (unsigned long)frame->length,
                 (unsigned long)frame->ts);
    }

    /* TODO(product-audio): copy/enqueue the encoded frame to a non-blocking
     * decoder/playback task when the product has a speaker. */
}

static void on_video(tirtc_conn_t connection, const TIRTCFRAMEINFO *frame, void *data)
{
    (void)data;
    if (frame == NULL || !is_active_connection(connection)) {
        return;
    }

    uint32_t count = (uint32_t)atomic_fetch_add_explicit(
                         &s_video_rx_frames, 1, memory_order_relaxed) + 1U;
    if (count <= 3U || count % 100U == 0U) {
        ESP_LOGI(TAG,
                 "RX video #%lu stream=%u codec=%s len=%lu ts=%lu key=%d; no display sink, dropped",
                 (unsigned long)count,
                 frame->stream_id,
                 media_name(frame->media),
                 (unsigned long)frame->length,
                 (unsigned long)frame->ts,
                 (frame->flags & TIRTC_FRAME_FLAG_KEY_FRAME) != 0);
    }

    /* This target is audio-only. Unexpected downlink video is discarded. */
}

/* The callback table must outlive TiRtcStart/TiRtcStop. */
static const TIRTCCALLBACKS s_callbacks = {
    .on_event = on_event,
    .on_conn_accepted = on_conn_accepted,
    .on_conn_error = on_conn_error,
    .on_disconnected = on_disconnected,
    .on_audio = on_audio,
    .on_video = on_video,
    .on_command = on_command,
    .on_request_key_frame = on_request_key_frame,
    .on_subscribe_video = on_subscribe_video,
    .on_unsubscribe_video = on_unsubscribe,
    .on_subscribe_audio = on_subscribe_audio,
    .on_unsubscribe_audio = on_unsubscribe,
    /* This audio-only target has no video encoder bitrate to adjust. */
    .on_update_bitrate = NULL,
    .on_sleep_wakeup_info = NULL,
};

static int set_string_option(TIRTCOPTION option, const char *value)
{
    if (value == NULL || value[0] == '\0') {
        return 0;
    }
    return TiRtcSetOption(option, value, (uint32_t)strlen(value));
}

const char *tirtc_adapter_version(void)
{
    return TiRtcGetVersion();
}

const char *tirtc_adapter_build_info(void)
{
    return TiRtcGetBuildInfo();
}

tirtc_adapter_state_t tirtc_adapter_state(void)
{
    return s_state;
}

int tirtc_adapter_start(const tirtc_adapter_config_t *config)
{
    if (config == NULL || config->device_id == NULL || config->device_id[0] == '\0' ||
        config->device_secret == NULL || config->device_secret[0] == '\0') {
        return TIRTC_E_INVALID_PARAMETER;
    }
    if (s_state != TIRTC_ADAPTER_IDLE) {
        return TIRTC_E_BUSY;
    }
    atomic_store_explicit(&s_active_connection, 0, memory_order_release);
    atomic_store_explicit(&s_active_connection_generation, 0, memory_order_release);
    atomic_store_explicit(&s_active_connection_request_tag, 0, memory_order_release);
    atomic_store_explicit(&s_connect_request_pending, false, memory_order_release);
    atomic_store_explicit(&s_connect_request_tag, 0, memory_order_release);
    clear_media_subscriptions();
    (void)atomic_fetch_add_explicit(
        &s_connect_request_generation, 1, memory_order_release);

    TiRtcLogSetCallback(sdk_log);
    TiRtcLogSetLevel(config->log_level > 0 ? config->log_level : 3);

    int rc = 0;
    if (config->max_send_buffer_bytes > 0) {
        rc = TiRtcSetOption(TIRTC_OPT_MAX_SEND_BUFFER,
                            &config->max_send_buffer_bytes,
                            sizeof(config->max_send_buffer_bytes));
        if (rc != 0) {
            goto fail;
        }
    }

    rc = TiRtcInit();
    if (rc != 0) {
        goto fail;
    }
    s_initialized = true;

    rc = set_string_option(TIRTC_OPT_DEVICE_SECRET_KEY, config->device_secret);
    if (rc != 0) {
        goto fail;
    }
    rc = set_string_option(TIRTC_OPT_CLIENT_ID, config->client_id);
    if (rc != 0) {
        goto fail;
    }

    int network_type = TIRTC_NETCONN_WIFI;
    rc = TiRtcSetOption(TIRTC_OPT_NETWORK_TYPE, &network_type, sizeof(network_type));
    if (rc != 0) {
        goto fail;
    }

    if (config->max_connections > 0) {
        rc = TiRtcSetOption(TIRTC_OPT_MAX_CONNECTIONS,
                            &config->max_connections,
                            sizeof(config->max_connections));
        if (rc != 0) {
            goto fail;
        }
    }

    s_state = TIRTC_ADAPTER_STARTING;
    rc = TiRtcStart(config->device_id, &s_callbacks);
    if (rc != 0) {
        goto fail;
    }

    ESP_LOGI(TAG, "TiRTC start submitted for device_id=%s", config->device_id);
    return 0;

fail:
    if (s_initialized) {
        TiRtcUninit();
        s_initialized = false;
    }
    s_state = TIRTC_ADAPTER_ERROR;
    ESP_LOGE(TAG, "TiRTC start failed: %d (%s)", rc, TiRtcGetErrorStr(rc));
    return rc;
}

int tirtc_adapter_request_stop(void)
{
    if (s_state != TIRTC_ADAPTER_STARTING && s_state != TIRTC_ADAPTER_RUNNING) {
        return TIRTC_E_NOT_INITIALIZED;
    }
    (void)tirtc_adapter_disconnect();
    int rc = TiRtcStop();
    if (rc == 0) {
        s_state = TIRTC_ADAPTER_STOPPING;
    }
    return rc;
}

int tirtc_adapter_deinit(void)
{
    if (s_state != TIRTC_ADAPTER_STOPPED && s_state != TIRTC_ADAPTER_ERROR) {
        return TIRTC_E_BUSY;
    }
    if (s_initialized) {
        TiRtcUninit();
        s_initialized = false;
    }
    s_state = TIRTC_ADAPTER_IDLE;
    return 0;
}

bool tirtc_adapter_has_connection(void)
{
    return atomic_load_explicit(&s_active_connection, memory_order_acquire) != 0;
}

uint32_t tirtc_adapter_connection_generation(void)
{
    return (uint32_t)atomic_load_explicit(&s_connection_generation, memory_order_acquire);
}

int tirtc_adapter_connect(const char *remote_id,
                          const char *token,
                          uint32_t request_tag)
{
    if (s_state != TIRTC_ADAPTER_RUNNING || remote_id == NULL || remote_id[0] == '\0') {
        return TIRTC_E_INVALID_PARAMETER;
    }
    bool expected_pending = false;
    if (tirtc_adapter_has_connection() ||
        !atomic_compare_exchange_strong_explicit(&s_connect_request_pending,
                                                  &expected_pending,
                                                  true,
                                                  memory_order_acq_rel,
                                                  memory_order_acquire)) {
        return TIRTC_E_BUSY;
    }
    uint32_t request_generation = (uint32_t)atomic_fetch_add_explicit(
                                      &s_connect_request_generation,
                                      1,
                                      memory_order_acq_rel) +
                                  1U;
    atomic_store_explicit(&s_connect_request_tag, request_tag, memory_order_release);
    int rc = TiRtcConnect(remote_id,
                          token,
                          on_connect_result,
                          (void *)(uintptr_t)request_generation);
    if (rc != 0 &&
        request_generation ==
            atomic_load_explicit(&s_connect_request_generation, memory_order_acquire)) {
        atomic_store_explicit(&s_connect_request_pending, false, memory_order_release);
    }
    return rc;
}

int tirtc_adapter_disconnect(void)
{
    (void)atomic_fetch_add_explicit(
        &s_connect_request_generation, 1, memory_order_acq_rel);
    atomic_store_explicit(&s_connect_request_pending, false, memory_order_release);
    tirtc_conn_t connection = (tirtc_conn_t)atomic_exchange_explicit(
        &s_active_connection, 0, memory_order_acq_rel);
    if (connection == NULL) {
        return TIRTC_E_INVALID_HANDLE;
    }
    clear_media_subscriptions();
    atomic_store_explicit(&s_active_connection_generation, 0, memory_order_release);
    atomic_store_explicit(&s_active_connection_request_tag, 0, memory_order_release);
    return TiRtcDisconnect(connection);
}

int tirtc_adapter_whip_connect(const char *service_description,
                               const char *token,
                               uint32_t request_tag)
{
    if (s_state != TIRTC_ADAPTER_RUNNING || service_description == NULL ||
        service_description[0] == '\0' || token == NULL || token[0] == '\0') {
        ESP_LOGE(TAG,
                 "WHIP connect rejected before SDK: adapter-state=%d description=%s token=%s",
                 (int)s_state,
                 service_description != NULL && service_description[0] != '\0'
                     ? "present"
                     : "missing",
                 token != NULL && token[0] != '\0' ? "present" : "missing");
        return TIRTC_E_INVALID_PARAMETER;
    }
    bool expected_pending = false;
    if (tirtc_adapter_has_connection() ||
        !atomic_compare_exchange_strong_explicit(&s_connect_request_pending,
                                                  &expected_pending,
                                                  true,
                                                  memory_order_acq_rel,
                                                  memory_order_acquire)) {
        ESP_LOGE(TAG,
                 "WHIP connect rejected before SDK: connection=%s request-pending=%s",
                 tirtc_adapter_has_connection() ? "active" : "none",
                 expected_pending ? "yes" : "no");
        return TIRTC_E_BUSY;
    }
    ESP_LOGI(TAG,
             "submitting WHIP connect description-length=%u token-length=%u",
             (unsigned)strlen(service_description),
             (unsigned)strlen(token));
    uint32_t request_generation = (uint32_t)atomic_fetch_add_explicit(
                                      &s_connect_request_generation,
                                      1,
                                      memory_order_acq_rel) +
                                  1U;
    atomic_store_explicit(&s_connect_request_tag, request_tag, memory_order_release);
    int rc = TiRtcWhipConnect(service_description,
                              token,
                              on_connect_result,
                              (void *)(uintptr_t)request_generation);
    if (rc != 0 &&
        request_generation ==
            atomic_load_explicit(&s_connect_request_generation, memory_order_acquire)) {
        atomic_store_explicit(&s_connect_request_pending, false, memory_order_release);
    }
    if (rc != 0) {
        ESP_LOGE(TAG,
                 "WHIP connect submission failed: %d (%s)",
                 rc,
                 TiRtcGetErrorStr(rc));
    } else {
        ESP_LOGI(TAG, "WHIP connect request submitted");
    }
    return rc;
}

int tirtc_adapter_send_command(uint32_t command,
                               const void *data,
                               uint32_t length)
{
    tirtc_conn_t connection = (tirtc_conn_t)atomic_load_explicit(
        &s_active_connection, memory_order_acquire);
    if (connection == NULL) {
        return TIRTC_E_INVALID_HANDLE;
    }
    return TiRtcSendCommand(connection, command, data, length);
}

int tirtc_adapter_disable_video_downlink(void)
{
    tirtc_conn_t connection = (tirtc_conn_t)atomic_load_explicit(
        &s_active_connection, memory_order_acquire);
    if (connection == NULL) {
        return TIRTC_E_INVALID_HANDLE;
    }

    int rc = TiRtcUnsubscribeVideo(connection, STREAM_ID_VIDEO);
    if (rc >= 0) {
        ESP_LOGI(TAG,
                 "video downlink stream=%u unsubscribed: ESP32-S3 target is audio-only",
                 STREAM_ID_VIDEO);
    } else {
        ESP_LOGW(TAG,
                 "video downlink unsubscribe stream=%u failed rc=%d (%s)",
                 STREAM_ID_VIDEO,
                 rc,
                 TiRtcGetErrorStr(rc));
    }
    return rc;
}

int tirtc_adapter_service_request(const char *path,
                                  const char *json_body,
                                  const char *token,
                                  tirtc_adapter_service_callback_t callback,
                                  void *user_data)
{
    if (s_state != TIRTC_ADAPTER_RUNNING || path == NULL || path[0] == '\0') {
        return TIRTC_E_NOT_INITIALIZED;
    }
    return TiRtcServiceRequest(path,
                               json_body,
                               token,
                               (TIRTCSERVICEREQUESTCALLBACK)callback,
                               user_data);
}

bool tirtc_adapter_audio_subscribed(void)
{
    return atomic_load_explicit(&s_audio_subscribed, memory_order_acquire);
}

bool tirtc_adapter_audio_uplink_ready(void)
{
    if (!tirtc_adapter_has_connection()) {
        return false;
    }
    bool incoming =
        atomic_load_explicit(&s_connection_incoming, memory_order_acquire);
    return !incoming || tirtc_adapter_audio_subscribed();
}

size_t tirtc_adapter_send_buffer_used(void)
{
    tirtc_conn_t connection = (tirtc_conn_t)atomic_load_explicit(
        &s_active_connection, memory_order_acquire);
    return connection != NULL ? TiRtcGetSendBufferUsed(connection) : 0;
}

void tirtc_adapter_set_event_handlers(const tirtc_adapter_event_handlers_t *handlers)
{
    if (handlers == NULL) {
        memset(&s_event_handlers, 0, sizeof(s_event_handlers));
    } else {
        s_event_handlers = *handlers;
    }
}

static uint8_t audio_media(device_audio_codec_t codec)
{
    switch (codec) {
    case DEVICE_AUDIO_CODEC_ALAW: return TIRTC_AUDIO_ALAW;
    case DEVICE_AUDIO_CODEC_AMR_NB:
    case DEVICE_AUDIO_CODEC_AMR_WB: return TIRTC_AUDIO_AMR;
    case DEVICE_AUDIO_CODEC_OPUS: return TIRTC_AUDIO_OPUS;
    default: return 0;
    }
}

int tirtc_adapter_send_audio(const device_audio_config_t *config,
                             uint32_t timestamp_ms,
                             const void *data,
                             uint32_t length)
{
    tirtc_conn_t connection = (tirtc_conn_t)atomic_load_explicit(
        &s_active_connection, memory_order_acquire);
    if (connection == NULL) {
        return TIRTC_E_INVALID_HANDLE;
    }
    if (config == NULL || data == NULL || length == 0) {
        return TIRTC_E_INVALID_PARAMETER;
    }

    uint8_t media = audio_media(config->codec);
    if (media == 0 || config->channels != 1 ||
        (config->sample_rate_hz != 8000 && config->sample_rate_hz != 16000)) {
        return TIRTC_E_INVALID_PARAMETER;
    }

    TIRTCFRAMEINFO frame = {
        .stream_id = STREAM_ID_AUDIO,
        .media = media,
        .flags = config->sample_rate_hz == 8000
                     ? TIRTC_AUDIOSAMPLE_8K16B1C
                     : TIRTC_AUDIOSAMPLE_16K16B1C,
        .reserved = 0,
        .ts = timestamp_ms,
        .length = length,
    };
    return TiRtcSendAudioStream(connection, &frame, data);
}

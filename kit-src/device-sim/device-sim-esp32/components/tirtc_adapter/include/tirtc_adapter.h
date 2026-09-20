#ifndef TIRTC_ADAPTER_H
#define TIRTC_ADAPTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "device/device_media.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    TIRTC_ADAPTER_IDLE = 0,
    TIRTC_ADAPTER_STARTING,
    TIRTC_ADAPTER_RUNNING,
    TIRTC_ADAPTER_STOPPING,
    TIRTC_ADAPTER_STOPPED,
    TIRTC_ADAPTER_ERROR,
} tirtc_adapter_state_t;

typedef struct {
    const char *device_id;
    const char *device_secret;
    const char *client_id;
    uint32_t max_send_buffer_bytes;
    int max_connections;
    int log_level;
} tirtc_adapter_config_t;

typedef struct {
    void (*on_connection_changed)(bool connected,
                                  bool incoming,
                                  uint32_t connection_generation,
                                  uint32_t request_tag,
                                  void *user_data);
    void (*on_command)(uint32_t command,
                       const void *data,
                       uint32_t length,
                       uint32_t connection_generation,
                       void *user_data);
    void *user_data;
} tirtc_adapter_event_handlers_t;

typedef void (*tirtc_adapter_service_callback_t)(const char *body, void *user_data);

const char *tirtc_adapter_version(void);
const char *tirtc_adapter_build_info(void);
tirtc_adapter_state_t tirtc_adapter_state(void);

/* Call after networking and credentials are ready. No credential is logged. */
int tirtc_adapter_start(const tirtc_adapter_config_t *config);

/* Stop is asynchronous. Wait for STOPPED before calling deinit. */
int tirtc_adapter_request_stop(void);
int tirtc_adapter_deinit(void);

bool tirtc_adapter_has_connection(void);
uint32_t tirtc_adapter_connection_generation(void);
int tirtc_adapter_connect(const char *remote_id,
                          const char *token,
                          uint32_t request_tag);
int tirtc_adapter_disconnect(void);
int tirtc_adapter_whip_connect(const char *service_description,
                               const char *token,
                               uint32_t request_tag);
int tirtc_adapter_send_command(uint32_t command,
                               const void *data,
                               uint32_t length);
/* The ESP32-S3 target has no video sink. Ask the peer to stop stream 11. */
int tirtc_adapter_disable_video_downlink(void);
int tirtc_adapter_service_request(const char *path,
                                  const char *json_body,
                                  const char *token,
                                  tirtc_adapter_service_callback_t callback,
                                  void *user_data);
bool tirtc_adapter_audio_subscribed(void);
bool tirtc_adapter_audio_uplink_ready(void);
size_t tirtc_adapter_send_buffer_used(void);
void tirtc_adapter_set_event_handlers(const tirtc_adapter_event_handlers_t *handlers);

int tirtc_adapter_send_audio(const device_audio_config_t *config,
                             uint32_t timestamp_ms,
                             const void *data,
                             uint32_t length);

#ifdef __cplusplus
}
#endif

#endif

#ifndef SESSION_RUNTIME_H
#define SESSION_RUNTIME_H

#include "device/device_session.h"
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t session_runtime_start(void);
device_session_state_t session_runtime_state(void);
device_service_t session_runtime_service(void);

esp_err_t session_runtime_ai_press(void);
esp_err_t session_runtime_ai_release(void);
esp_err_t session_runtime_voip_call_default(void);
esp_err_t session_runtime_voip_connect(const char *service_description, const char *token);
esp_err_t session_runtime_contacts(void);
esp_err_t session_runtime_device_call_default(void);
esp_err_t session_runtime_device_call(const char *remote_device_id, const char *token);
esp_err_t session_runtime_accept(void);
esp_err_t session_runtime_reject(void);
esp_err_t session_runtime_cancel(void);
esp_err_t session_runtime_hangup(void);

#ifdef __cplusplus
}
#endif

#endif

#ifndef MEDIA_RUNTIME_H
#define MEDIA_RUNTIME_H

#include <stdbool.h>

#include "device/device_media.h"
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t media_runtime_init(void);
esp_err_t media_runtime_start(void);
void media_runtime_stop(void);
bool media_runtime_ready(void);
const device_media_config_t *media_runtime_config(void);
void media_runtime_set_uplink_active(bool active);
bool media_runtime_uplink_active(void);

#ifdef __cplusplus
}
#endif

#endif

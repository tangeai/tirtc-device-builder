#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#include "device_console.h"
#include "esp_chip_info.h"
#include "esp_heap_caps.h"
#include "esp_idf_version.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "media_runtime.h"
#include "nvs_flash.h"
#include "platform_client.h"
#include "runtime_config.h"
#include "session_runtime.h"
#include "tirtc_adapter.h"
#include "wifi_manager.h"

static const char *TAG = "device_main";
static runtime_tirtc_config_t s_tirtc_config;

#define START_RETRY_DELAY_MS 5000U

static void station_identity(char mac_address[18], char client_id[65])
{
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    (void)snprintf(mac_address,
                   18,
                   "%02X:%02X:%02X:%02X:%02X:%02X",
                   mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    (void)snprintf(client_id,
                   65,
                   "esp32s3-%02x%02x%02x%02x%02x%02x",
                   mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

static esp_err_t provision_and_save(const char *mac_address, bool signed_rebind)
{
    platform_provision_result_t provisioned = {0};
    const platform_provision_config_t provision = {
        .mac_address = mac_address,
        .existing_device_id = signed_rebind ? s_tirtc_config.device_id : NULL,
        .existing_device_secret = signed_rebind
                                      ? s_tirtc_config.device_secret
                                      : NULL,
        .timeout_seconds = 190,
    };
    esp_err_t err = platform_client_provision(&provision, &provisioned);
    if (err != ESP_OK) {
        return err;
    }
    (void)snprintf(s_tirtc_config.device_id,
                   sizeof(s_tirtc_config.device_id),
                   "%s",
                   provisioned.device_id);
    (void)snprintf(s_tirtc_config.device_secret,
                   sizeof(s_tirtc_config.device_secret),
                   "%s",
                   provisioned.device_secret);
    err = runtime_config_save_tirtc(&s_tirtc_config);
    if (err == ESP_OK) {
        ESP_LOGI(TAG,
                 "binding credentials saved to NVS for device_id=%s",
                 s_tirtc_config.device_id);
    } else {
        ESP_LOGE(TAG, "cannot save binding credentials: %s", esp_err_to_name(err));
    }
    return err;
}

static void tirtc_start_task(void *argument)
{
    (void)argument;
    while (!wifi_manager_connected()) {
        vTaskDelay(pdMS_TO_TICKS(250));
    }

    char mac_address[18];
    char default_client_id[65];
    station_identity(mac_address, default_client_id);

    esp_err_t err = runtime_config_load_tirtc(&s_tirtc_config);
    char validation_error[96];
    bool credentials_valid = err == ESP_OK &&
                             runtime_config_tirtc_valid(&s_tirtc_config,
                                                        validation_error,
                                                        sizeof(validation_error));
    if (!credentials_valid) {
        memset(&s_tirtc_config, 0, sizeof(s_tirtc_config));
        (void)snprintf(s_tirtc_config.client_id,
                       sizeof(s_tirtc_config.client_id),
                       "%s",
                       default_client_id);
        ESP_LOGW(TAG,
                 "device is not bound; starting verification-code binding automatically");
        err = provision_and_save(mac_address, false);
        if (err != ESP_OK) {
            ESP_LOGE(TAG,
                     "verification binding did not complete: %s; restart to retry",
                     esp_err_to_name(err));
            vTaskDelete(NULL);
            return;
        }
    }

    if (s_tirtc_config.client_id[0] == '\0') {
        (void)snprintf(s_tirtc_config.client_id,
                       sizeof(s_tirtc_config.client_id),
                       "%s",
                       default_client_id);
    }

    const platform_client_config_t platform = {
        .device_id = s_tirtc_config.device_id,
        .device_secret = s_tirtc_config.device_secret,
        .client_id = s_tirtc_config.client_id,
        .mac_address = mac_address,
    };
    bool rebind_attempted = false;
    bool tirtc_submitted = false;
    for (;;) {
        while (!wifi_manager_connected()) {
            vTaskDelay(pdMS_TO_TICKS(250));
        }

        if (!platform_client_ready()) {
            esp_err_t platform_result = platform_client_start(&platform);
            if (platform_result == ESP_ERR_NOT_FOUND && !rebind_attempted) {
                rebind_attempted = true;
                ESP_LOGW(TAG,
                         "stored device was unbound; starting signed verification rebind");
                platform_result = provision_and_save(mac_address, true);
                if (platform_result == ESP_OK) {
                    platform_result = platform_client_start(&platform);
                }
            }
            if (platform_result != ESP_OK) {
                ESP_LOGE(TAG,
                         "platform signaling unavailable: %s",
                         esp_err_to_name(platform_result));
            }
        }

        if (!tirtc_submitted) {
            if (tirtc_adapter_state() == TIRTC_ADAPTER_ERROR) {
                (void)tirtc_adapter_deinit();
            }
            const tirtc_adapter_config_t adapter = {
                .device_id = s_tirtc_config.device_id,
                .device_secret = s_tirtc_config.device_secret,
                .client_id = s_tirtc_config.client_id,
                .max_send_buffer_bytes = 256U * 1024U,
                .max_connections = 1,
                .log_level = 3,
            };
            int rc = tirtc_adapter_start(&adapter);
            if (rc == 0) {
                tirtc_submitted = true;
            } else {
                ESP_LOGE(TAG, "TiRTC start failed rc=%d", rc);
                if (tirtc_adapter_state() == TIRTC_ADAPTER_ERROR) {
                    (void)tirtc_adapter_deinit();
                }
            }
        }

        if (platform_client_ready() && tirtc_submitted) {
            break;
        }
        ESP_LOGW(TAG,
                 "startup incomplete; retrying platform/TiRTC in %u ms",
                 START_RETRY_DELAY_MS);
        vTaskDelay(pdMS_TO_TICKS(START_RETRY_DELAY_MS));
    }
    vTaskDelete(NULL);
}

static void init_nvs(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
}

void app_main(void)
{
    init_nvs();

    esp_chip_info_t chip;
    esp_chip_info(&chip);
    ESP_LOGI(TAG, "ESP-IDF %s, cores=%u, revision=%u",
             esp_get_idf_version(), chip.cores, chip.revision);
    ESP_LOGI(TAG, "heap internal=%" PRIu32 " bytes, PSRAM=%" PRIu32 " bytes",
             heap_caps_get_total_size(MALLOC_CAP_INTERNAL),
             heap_caps_get_total_size(MALLOC_CAP_SPIRAM));

    ESP_LOGI(TAG, "TiRTC version: %s", tirtc_adapter_version());
    ESP_LOGI(TAG, "TiRTC build: %s", tirtc_adapter_build_info());

    esp_err_t media_result = media_runtime_init();
    if (media_result == ESP_OK) {
        media_result = media_runtime_start();
    }
    if (media_result != ESP_OK) {
        ESP_LOGE(TAG, "media runtime unavailable: %s", esp_err_to_name(media_result));
    }

    esp_err_t wifi_result = wifi_manager_start();
    if (wifi_result != ESP_OK) {
        ESP_LOGE(TAG, "Wi-Fi manager unavailable: %s", esp_err_to_name(wifi_result));
    }

    esp_err_t session_result = session_runtime_start();
    if (session_result != ESP_OK) {
        ESP_LOGE(TAG, "session runtime unavailable: %s", esp_err_to_name(session_result));
    }

    esp_err_t console_result = device_console_start();
    if (console_result != ESP_OK) {
        ESP_LOGE(TAG, "serial console unavailable: %s", esp_err_to_name(console_result));
    }
    if (wifi_result == ESP_OK &&
        xTaskCreate(tirtc_start_task, "tirtc_start", 24576, NULL, 4, NULL) != pdPASS) {
        ESP_LOGE(TAG, "cannot create TiRTC start task");
    }
}

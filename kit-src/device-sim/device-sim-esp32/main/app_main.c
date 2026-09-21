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
static char s_station_mac[18];

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
    /* TODO(product-security): enable encrypted NVS or a secure element before
     * storing production device credentials. Never compile secrets into firmware. */
    /*
     * 首次绑定不带已有凭证；服务端解绑后的重绑使用旧凭证签名设备上报。
     * platform_client_provision() 阻塞等待用户输入验证码，因此本函数只能
     * 在启动/HTTP 工作任务中运行，不能放进 app_main 或 SDK 回调。
     */
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
    if (signed_rebind) {
        /* A signed Report reactivates this identity, including empty auth_grant
         * payloads. Keep the running SDK identity stable and avoid all flash
         * operations; a changed key/ID is a contract error, not a reason to
         * overwrite NVS underneath a running SDK. */
        bool same = strcmp(provisioned.device_id, s_tirtc_config.device_id) == 0 &&
                    strcmp(provisioned.device_secret, s_tirtc_config.device_secret) == 0;
        memset(&provisioned, 0, sizeof(provisioned));
        if (!same) {
            ESP_LOGE(TAG, "signed binding changed device identity; not applying");
            return ESP_ERR_INVALID_RESPONSE;
        }
        ESP_LOGI(TAG, "signed binding restored; NVS identity retained");
        return ESP_OK;
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

static esp_err_t rebind_platform(bool *binding_restored)
{
    esp_err_t err = platform_client_prepare_rebind();
    if (err != ESP_OK) return err;
    while (!wifi_manager_connected()) vTaskDelay(pdMS_TO_TICKS(100));
    const platform_client_config_t platform = {
        .device_id = s_tirtc_config.device_id,
        .device_secret = s_tirtc_config.device_secret,
        .client_id = s_tirtc_config.client_id,
        .mac_address = s_station_mac,
    };
    /* Missing a signal is not proof of unbind. Validate before asking the user
     * to bind again; a confirmed unbind goes straight to signed Report. */
    err = platform_client_known_unbound() && !*binding_restored
              ? ESP_ERR_NOT_FOUND : platform_client_start(&platform);
    if (err == ESP_ERR_NOT_FOUND) {
        err = provision_and_save(s_station_mac, true);
        if (err == ESP_OK) {
            *binding_restored = true;
            err = platform_client_start(&platform);
        }
    }
    if (err == ESP_OK) {
        platform_client_complete_rebind();
        ESP_LOGI(TAG, "binding transition complete; identity retained");
    }
    return err;
}

static void wait_for_network_clock(void)
{
    for (;;) {
        while (!wifi_manager_connected()) vTaskDelay(pdMS_TO_TICKS(100));
        esp_err_t err = platform_client_sync_clock();
        if (err == ESP_OK) return;
        ESP_LOGW(TAG, "startup waiting for network clock: %s; retrying in %u ms",
                 esp_err_to_name(err), START_RETRY_DELAY_MS);
        vTaskDelay(pdMS_TO_TICKS(START_RETRY_DELAY_MS));
    }
}

static void platform_request_task(void *argument)
{
    (void)argument;
    bool binding_restored = false;
    for (;;) {
        esp_err_t err = platform_client_run_request_loop();
        while (err == ESP_ERR_NOT_FOUND) {
            /* Runtime signalled a rebind: re-validate the stored identity and
             * signed-rebind on confirmed unbind, without clearing NVS. */
            ESP_LOGW(TAG, "binding transition requested; validating identity");
            err = rebind_platform(&binding_restored);
            if (err == ESP_ERR_NOT_FOUND) {
                ESP_LOGE(TAG, "rebind failed: %s; waiting for user retry",
                         esp_err_to_name(err));
                while (!platform_client_take_binding_retry()) vTaskDelay(pdMS_TO_TICKS(100));
                while (!wifi_manager_connected()) vTaskDelay(pdMS_TO_TICKS(100));
            }
        }
        if (err == ESP_OK) {
            continue;
        }
        ESP_LOGE(TAG,
                 "platform request loop unavailable: %s; retrying in %u ms",
                 esp_err_to_name(err), START_RETRY_DELAY_MS);
        vTaskDelay(pdMS_TO_TICKS(START_RETRY_DELAY_MS));
    }
}

static void tirtc_start_task(void *argument)
{
    (void)argument;
    /* Both stored credentials and first binding must cross the same clock
     * boundary before any SDK initialization or authenticated network I/O. */
    wait_for_network_clock();

    char mac_address[18];
    char default_client_id[65];
    station_identity(mac_address, default_client_id);
    (void)snprintf(s_station_mac, sizeof(s_station_mac), "%s", mac_address);

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
        do {
            err = provision_and_save(mac_address, false);
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "binding failed: %s; waiting for user retry",
                         esp_err_to_name(err));
                while (!platform_client_take_binding_retry()) vTaskDelay(pdMS_TO_TICKS(100));
                while (!wifi_manager_connected()) vTaskDelay(pdMS_TO_TICKS(100));
            }
        } while (err != ESP_OK);
    } else {
        ESP_LOGI(TAG, "stored device binding found; skipping verification-code binding");
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
        /* Normally a cache hit; also covers a retry after time became invalid. */
        wait_for_network_clock();

        if (!platform_client_ready()) {
            esp_err_t platform_result = platform_client_start(&platform);
            if (platform_result == ESP_ERR_NOT_FOUND && !rebind_attempted) {
                rebind_attempted = true;
                ESP_LOGW(TAG,
                         "stored device was unbound; starting signed verification rebind");
                do {
                    platform_result = provision_and_save(mac_address, true);
                    if (platform_result != ESP_OK) {
                        while (!platform_client_take_binding_retry()) vTaskDelay(pdMS_TO_TICKS(100));
                        while (!wifi_manager_connected()) vTaskDelay(pdMS_TO_TICKS(100));
                    }
                } while (platform_result != ESP_OK);
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

        if ((platform_client_ready() || platform_client_reconciling()) && tirtc_submitted) {
            break;
        }
        ESP_LOGW(TAG,
                 "startup incomplete; retrying platform/TiRTC in %u ms",
                 START_RETRY_DELAY_MS);
        vTaskDelay(pdMS_TO_TICKS(START_RETRY_DELAY_MS));
    }
    /* TiRTC/TLS startup is over; hand the identity lifecycle to a dedicated
     * HTTP worker that owns rebind transitions and the 30 s heartbeat. */
    if (xTaskCreate(platform_request_task, "platform_http", 24576, NULL, 5, NULL) != pdPASS) {
        ESP_LOGE(TAG, "cannot create platform HTTP task");
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

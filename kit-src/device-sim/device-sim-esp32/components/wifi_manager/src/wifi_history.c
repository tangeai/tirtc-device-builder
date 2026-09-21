#include "wifi_history.h"

#include <string.h>
#include "esp_attr.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "nvs.h"

#define WIFI_HISTORY_NAMESPACE "wifi_cfg"
#define WIFI_HISTORY_KEY "known"
#define WIFI_HISTORY_VERSION 1U

_Static_assert(sizeof(wifi_history_t) == 394, "Wi-Fi history layout changed");

/* Only the synchronization primitive is internal. Credentials and scratch data
 * are external; Flash access stays direct NVS (nvs_* is thread-safe on both
 * targets; the P4 product's async nvs_store worker is not required here). */
static StaticSemaphore_t s_mutex_storage;
static SemaphoreHandle_t s_mutex;
static EXT_RAM_BSS_ATTR wifi_manager_credentials_t s_active;
static bool s_allow_remember;

static esp_err_t history_read(wifi_history_t *history, size_t *size)
{
    nvs_handle_t nvs = 0;
    esp_err_t err = nvs_open(WIFI_HISTORY_NAMESPACE, NVS_READONLY, &nvs);
    if (err != ESP_OK) {
        return err;
    }
    err = nvs_get_blob(nvs, WIFI_HISTORY_KEY, history, size);
    nvs_close(nvs);
    return err;
}

static esp_err_t history_write(const wifi_history_t *history)
{
    nvs_handle_t nvs = 0;
    esp_err_t err = nvs_open(WIFI_HISTORY_NAMESPACE, NVS_READWRITE, &nvs);
    if (err == ESP_OK) {
        err = nvs_set_blob(nvs, WIFI_HISTORY_KEY, history, sizeof(*history));
    }
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    if (nvs != 0) {
        nvs_close(nvs);
    }
    return err;
}

void wifi_history_init(const wifi_manager_credentials_t *active)
{
    if (s_mutex == NULL) s_mutex = xSemaphoreCreateMutexStatic(&s_mutex_storage);
    s_allow_remember = active != NULL;
    memset(&s_active, 0, sizeof(s_active));
    if (active != NULL) s_active = *active;
}

esp_err_t wifi_history_load(wifi_history_t *history)
{
    if (history == NULL) return ESP_ERR_INVALID_ARG;
    memset(history, 0, sizeof(*history));
    size_t size = sizeof(*history);
    esp_err_t err = history_read(history, &size);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        memset(history, 0, sizeof(*history));
        history->version = WIFI_HISTORY_VERSION;
        return ESP_OK;
    }
    if (err != ESP_OK) return err;
    if (size != sizeof(*history) || history->version != WIFI_HISTORY_VERSION ||
        history->count > WIFI_HISTORY_CAPACITY) return ESP_ERR_INVALID_RESPONSE;
    for (size_t i = 0; i < history->count; ++i) {
        const wifi_manager_credentials_t *entry = &history->entries[i];
        if (memchr(entry->ssid, 0, sizeof(entry->ssid)) == NULL ||
            memchr(entry->password, 0, sizeof(entry->password)) == NULL ||
            !wifi_manager_credentials_valid(entry->ssid, entry->password, NULL, 0))
            return ESP_ERR_INVALID_RESPONSE;
        for (size_t j = 0; j < i; ++j) {
            if (strcmp(entry->ssid, history->entries[j].ssid) == 0)
                return ESP_ERR_INVALID_RESPONSE;
        }
    }
    return ESP_OK;
}

esp_err_t wifi_history_remember_active(void)
{
    if (s_mutex == NULL) return ESP_ERR_INVALID_STATE;
    wifi_history_t *history = heap_caps_malloc(sizeof(*history), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (history == NULL) return ESP_ERR_NO_MEM;
    esp_err_t err = ESP_ERR_TIMEOUT;
    if (xSemaphoreTake(s_mutex, pdMS_TO_TICKS(5000)) == pdTRUE) {
        if (!s_allow_remember) {
            err = ESP_OK;
        } else {
            err = wifi_history_load(history);
            if (err == ESP_OK && (history->count == 0 ||
                memcmp(&history->entries[0], &s_active, sizeof(s_active)) != 0)) {
                size_t index = 0;
                while (index < history->count &&
                       strcmp(history->entries[index].ssid, s_active.ssid) != 0) ++index;
                if (index == history->count && history->count < WIFI_HISTORY_CAPACITY)
                    ++history->count;
                if (index >= WIFI_HISTORY_CAPACITY) index = WIFI_HISTORY_CAPACITY - 1;
                memmove(&history->entries[1], &history->entries[0], index * sizeof(s_active));
                history->entries[0] = s_active;
                err = history_write(history);
            }
        }
        xSemaphoreGive(s_mutex);
    }
    memset(history, 0, sizeof(*history));
    heap_caps_free(history);
    return err;
}

esp_err_t wifi_history_forget_all(void)
{
    if (s_mutex != NULL && xSemaphoreTake(s_mutex, pdMS_TO_TICKS(5000)) != pdTRUE)
        return ESP_ERR_TIMEOUT;
    /* Serialize with a queued GOT_IP update. Forgetting must not be undone by
     * a late worker notification, even if the erase completion times out. */
    s_allow_remember = false;
    memset(&s_active, 0, sizeof(s_active));
    nvs_handle_t nvs = 0;
    esp_err_t err = nvs_open(WIFI_HISTORY_NAMESPACE, NVS_READWRITE, &nvs);
    if (err == ESP_OK) {
        err = nvs_erase_all(nvs);
    }
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    if (nvs != 0) {
        nvs_close(nvs);
    }
    if (s_mutex != NULL) xSemaphoreGive(s_mutex);
    return err;
}

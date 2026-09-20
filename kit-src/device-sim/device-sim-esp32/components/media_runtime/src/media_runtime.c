#include "media_runtime.h"

#include <errno.h>
#include <stdio.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "cJSON.h"
#include "device/device_media_file.h"
#include "esp_log.h"
#include "esp_spiffs.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "tirtc_adapter.h"

#define MEDIA_MOUNT_POINT "/media"
#define MEDIA_PROFILE_PATH MEDIA_MOUNT_POINT "/media_profile.json"
#define MEDIA_JSON_MAX_BYTES 8192U
#define MEDIA_AUDIO_BUFFER_BYTES 1500U

typedef struct {
    device_alaw_file_t alaw;
    device_amr_file_t amr;
    device_opus_packet_file_t opus;
} audio_source_t;

static const char *TAG = "media_runtime";
static device_media_config_t s_config;
static bool s_ready;
static atomic_bool s_tasks_running;
static atomic_bool s_uplink_active;
static TaskHandle_t s_audio_task;

static bool json_u32(const cJSON *object, const char *name, uint32_t *value)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (!cJSON_IsNumber(item) || item->valuedouble < 0 ||
        item->valuedouble > UINT32_MAX ||
        item->valuedouble != (double)(uint32_t)item->valuedouble) {
        return false;
    }
    *value = (uint32_t)item->valuedouble;
    return true;
}

static bool json_bool(const cJSON *object, const char *name, bool *value)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (!cJSON_IsBool(item)) {
        return false;
    }
    *value = cJSON_IsTrue(item);
    return true;
}

static bool json_optional_u16(const cJSON *object, const char *name, uint16_t *value)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (item == NULL) {
        return true;
    }
    if (!cJSON_IsNumber(item) || item->valuedouble < 0 ||
        item->valuedouble > UINT16_MAX ||
        item->valuedouble != (double)(uint16_t)item->valuedouble) {
        return false;
    }
    *value = (uint16_t)item->valuedouble;
    return true;
}

static bool json_optional_positive_number(const cJSON *object,
                                          const char *name,
                                          double *value)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (item == NULL) {
        return true;
    }
    if (!cJSON_IsNumber(item) || item->valuedouble <= 0) {
        return false;
    }
    *value = item->valuedouble;
    return true;
}

static bool json_optional_bool(const cJSON *object, const char *name, bool *value)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (item == NULL) {
        return true;
    }
    if (!cJSON_IsBool(item)) {
        return false;
    }
    *value = cJSON_IsTrue(item);
    return true;
}

static bool json_optional_string(const cJSON *object,
                                 const char *name,
                                 char *value,
                                 size_t value_size)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (item == NULL) {
        return true;
    }
    if (!cJSON_IsString(item) || item->valuestring == NULL ||
        strlen(item->valuestring) >= value_size) {
        return false;
    }
    (void)snprintf(value, value_size, "%s", item->valuestring);
    return true;
}

static bool json_string(const cJSON *object,
                        const char *name,
                        char *value,
                        size_t value_size)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (!cJSON_IsString(item) || item->valuestring == NULL || item->valuestring[0] == '\0' ||
        strlen(item->valuestring) >= value_size) {
        return false;
    }
    (void)snprintf(value, value_size, "%s", item->valuestring);
    return true;
}

static bool json_file_name(const cJSON *object,
                           const char *name,
                           char *value,
                           size_t value_size)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (!cJSON_IsString(item) || item->valuestring == NULL ||
        strlen(item->valuestring) >= value_size) {
        return false;
    }
    (void)snprintf(value, value_size, "%s", item->valuestring);
    return true;
}

static bool parse_video_codec(const char *name, device_video_codec_t *codec)
{
    if (strcmp(name, "mjpeg") == 0) {
        *codec = DEVICE_VIDEO_CODEC_MJPEG;
    } else if (strcmp(name, "h264") == 0) {
        *codec = DEVICE_VIDEO_CODEC_H264;
    } else {
        return false;
    }
    return true;
}

static esp_err_t load_json_file(const char *path, char **text, size_t *length)
{
    FILE *file = fopen(path, "rb");
    if (file == NULL) {
        ESP_LOGE(TAG, "cannot open %s: errno=%d", path, errno);
        return ESP_ERR_NOT_FOUND;
    }
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return ESP_FAIL;
    }
    long file_length = ftell(file);
    if (file_length <= 0 || (unsigned long)file_length > MEDIA_JSON_MAX_BYTES ||
        fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return ESP_ERR_INVALID_SIZE;
    }

    char *buffer = malloc((size_t)file_length + 1U);
    if (buffer == NULL) {
        fclose(file);
        return ESP_ERR_NO_MEM;
    }
    size_t count = fread(buffer, 1, (size_t)file_length, file);
    fclose(file);
    if (count != (size_t)file_length) {
        free(buffer);
        return ESP_FAIL;
    }
    buffer[count] = '\0';
    *text = buffer;
    *length = count;
    return ESP_OK;
}

static esp_err_t load_profile(device_media_config_t *config)
{
    char *text = NULL;
    size_t length = 0;
    esp_err_t err = load_json_file(MEDIA_PROFILE_PATH, &text, &length);
    if (err != ESP_OK) {
        return err;
    }

    cJSON *root = cJSON_ParseWithLength(text, length);
    free(text);
    if (root == NULL) {
        ESP_LOGE(TAG, "invalid JSON in %s", MEDIA_PROFILE_PATH);
        return ESP_ERR_INVALID_ARG;
    }

    device_media_config_set_defaults(config);
    cJSON *audio = cJSON_GetObjectItemCaseSensitive(root, "audio");
    cJSON *video = cJSON_GetObjectItemCaseSensitive(root, "video");
    char audio_codec[16];
    char video_codec[16];
    uint32_t channels;
    uint32_t packet_ms;
    uint32_t width;
    uint32_t height;
    uint32_t fps;

    bool ok = cJSON_IsObject(audio) && cJSON_IsObject(video) &&
              json_optional_u16(video, "camera_rotation",
                                &config->video.camera_rotation) &&
              json_optional_u16(video, "down_video_rotation",
                                &config->video.down_video_rotation) &&
              json_optional_positive_number(video, "aspect_ratio",
                                            &config->video.aspect_ratio) &&
              json_optional_string(video, "object_fit",
                                   config->video.object_fit,
                                   sizeof(config->video.object_fit)) &&
              json_optional_bool(video, "hor_mirror",
                                 &config->video.hor_mirror) &&
              json_optional_bool(video, "vert_mirror",
                                 &config->video.vert_mirror) &&
              json_string(audio, "file", config->audio.asset_path,
                          sizeof(config->audio.asset_path)) &&
              json_string(audio, "codec", audio_codec, sizeof(audio_codec)) &&
              device_audio_codec_parse(audio_codec, &config->audio.codec) &&
              json_u32(audio, "sample_rate_hz", &config->audio.sample_rate_hz) &&
              json_u32(audio, "channels", &channels) && channels <= UINT8_MAX &&
              json_u32(audio, "packet_ms", &packet_ms) && packet_ms <= UINT16_MAX &&
              json_u32(audio, "duration_ms", &config->audio.duration_ms) &&
              json_u32(audio, "packet_count", &config->audio.packet_count) &&
              json_file_name(video, "file", config->video.asset_path,
                             sizeof(config->video.asset_path)) &&
              json_string(video, "codec", video_codec, sizeof(video_codec)) &&
              parse_video_codec(video_codec, &config->video.codec) &&
              json_u32(video, "width", &width) && width <= UINT16_MAX &&
              json_u32(video, "height", &height) && height <= UINT16_MAX &&
              json_u32(video, "fps", &fps) && fps <= UINT16_MAX &&
              json_u32(video, "duration_ms", &config->video.duration_ms) &&
              json_u32(video, "frame_count", &config->video.frame_count) &&
              json_bool(video, "uplink_enabled", &config->video.uplink_enabled) &&
              json_bool(video, "downlink_enabled", &config->video.downlink_enabled);

    if (ok) {
        config->audio.channels = (uint8_t)channels;
        config->audio.packet_ms = (uint16_t)packet_ms;
        config->video.width = (uint16_t)width;
        config->video.height = (uint16_t)height;
        config->video.fps = (uint16_t)fps;
    }
    cJSON_Delete(root);

    char validation_error[128];
    if (!ok || !device_media_config_validate(config,
                                              validation_error,
                                              sizeof(validation_error))) {
        ESP_LOGE(TAG, "invalid media profile: %s",
                 ok ? validation_error : "missing or invalid field");
        return ESP_ERR_INVALID_ARG;
    }
    if (config->video.uplink_enabled || config->video.downlink_enabled) {
        ESP_LOGE(TAG,
                 "invalid media profile: ESP32-S3 target is audio-only");
        return ESP_ERR_NOT_SUPPORTED;
    }
    if (strchr(config->audio.asset_path, '/') != NULL ||
        strchr(config->video.asset_path, '/') != NULL) {
        ESP_LOGE(TAG, "asset paths must be file names in %s", MEDIA_MOUNT_POINT);
        return ESP_ERR_INVALID_ARG;
    }
    return ESP_OK;
}

static void asset_path(char *path, size_t path_size, const char *file_name)
{
    (void)snprintf(path, path_size, MEDIA_MOUNT_POINT "/%s", file_name);
}

static device_media_file_result_t open_audio_source(audio_source_t *source,
                                                    const char *path)
{
    size_t fixed_packet_bytes =
        s_config.audio.sample_rate_hz * s_config.audio.packet_ms / 1000U;
    switch (s_config.audio.codec) {
    case DEVICE_AUDIO_CODEC_ALAW:
        return device_alaw_file_open(&source->alaw, path, fixed_packet_bytes);
    case DEVICE_AUDIO_CODEC_AMR_NB:
        return device_amr_file_open(&source->amr, path, false);
    case DEVICE_AUDIO_CODEC_AMR_WB:
        return device_amr_file_open(&source->amr, path, true);
    case DEVICE_AUDIO_CODEC_OPUS:
        return device_opus_packet_file_open(&source->opus, path);
    default:
        return DEVICE_MEDIA_FILE_INVALID;
    }
}

static device_media_file_result_t next_audio_packet(audio_source_t *source,
                                                    uint8_t *buffer,
                                                    size_t capacity,
                                                    size_t *size,
                                                    bool loop)
{
    switch (s_config.audio.codec) {
    case DEVICE_AUDIO_CODEC_ALAW:
        return device_alaw_file_next(&source->alaw, buffer, capacity, size, loop);
    case DEVICE_AUDIO_CODEC_AMR_NB:
    case DEVICE_AUDIO_CODEC_AMR_WB:
        return device_amr_file_next(&source->amr, buffer, capacity, size, loop);
    case DEVICE_AUDIO_CODEC_OPUS:
        return device_opus_packet_file_next(&source->opus,
                                            buffer,
                                            capacity,
                                            size,
                                            loop);
    default:
        return DEVICE_MEDIA_FILE_INVALID;
    }
}

static bool audio_source_is_open(const audio_source_t *source)
{
    return source->alaw.file != NULL || source->amr.file != NULL ||
           source->opus.file != NULL;
}

static void close_audio_source(audio_source_t *source)
{
    device_alaw_file_close(&source->alaw);
    device_amr_file_close(&source->amr);
    device_opus_packet_file_close(&source->opus);
}

static esp_err_t validate_assets(void)
{
    char audio_path[DEVICE_MEDIA_ASSET_PATH_MAX + sizeof(MEDIA_MOUNT_POINT)];
    asset_path(audio_path, sizeof(audio_path), s_config.audio.asset_path);

    struct stat info;
    uint32_t audio_packet_bytes =
        s_config.audio.sample_rate_hz * s_config.audio.packet_ms / 1000U;
    uint32_t expected_audio_bytes = audio_packet_bytes * s_config.audio.packet_count;
    if (s_config.audio.codec == DEVICE_AUDIO_CODEC_ALAW &&
        (stat(audio_path, &info) != 0 || info.st_size != (off_t)expected_audio_bytes)) {
        long actual = stat(audio_path, &info) == 0 ? (long)info.st_size : -1L;
        ESP_LOGE(TAG,
                 "audio asset mismatch: %s expected=%lu bytes actual=%ld",
                 audio_path,
                 (unsigned long)expected_audio_bytes,
                 actual);
        return ESP_ERR_INVALID_SIZE;
    }

    if (s_config.audio.codec != DEVICE_AUDIO_CODEC_ALAW) {
        audio_source_t source = {0};
        uint8_t packet[MEDIA_AUDIO_BUFFER_BYTES];
        device_media_file_result_t audio_result = open_audio_source(&source, audio_path);
        uint32_t packet_count = 0;
        size_t largest_packet = 0;
        if (audio_result == DEVICE_MEDIA_FILE_OK) {
            for (;;) {
                size_t packet_size = 0;
                audio_result = next_audio_packet(&source,
                                                 packet,
                                                 sizeof(packet),
                                                 &packet_size,
                                                 false);
                if (audio_result == DEVICE_MEDIA_FILE_EOF) {
                    break;
                }
                if (audio_result != DEVICE_MEDIA_FILE_OK) {
                    break;
                }
                packet_count++;
                if (packet_size > largest_packet) {
                    largest_packet = packet_size;
                }
                if ((packet_count & 0x0fU) == 0U) {
                    vTaskDelay(1);
                }
            }
        }
        close_audio_source(&source);
        if (audio_result != DEVICE_MEDIA_FILE_EOF ||
            packet_count != s_config.audio.packet_count) {
            ESP_LOGE(TAG,
                     "audio asset mismatch: %s expected=%lu packets actual=%lu result=%s",
                     audio_path,
                     (unsigned long)s_config.audio.packet_count,
                     (unsigned long)packet_count,
                     device_media_file_result_name(audio_result));
            return ESP_ERR_INVALID_SIZE;
        }
        ESP_LOGI(TAG, "variable audio verified: packets=%lu max-packet=%u bytes",
                 (unsigned long)packet_count, (unsigned)largest_packet);
    }

    ESP_LOGI(TAG,
             "assets verified: audio=%lu packets; video unsupported",
             (unsigned long)s_config.audio.packet_count);
    return ESP_OK;
}

static bool open_audio_asset(audio_source_t *audio)
{
    char audio_path[DEVICE_MEDIA_ASSET_PATH_MAX + sizeof(MEDIA_MOUNT_POINT)];
    asset_path(audio_path, sizeof(audio_path), s_config.audio.asset_path);
    return open_audio_source(audio, audio_path) == DEVICE_MEDIA_FILE_OK;
}

static void audio_sender_task(void *argument)
{
    (void)argument;
    uint8_t audio_packet[MEDIA_AUDIO_BUFFER_BYTES];
    audio_source_t audio = {0};
    uint32_t generation = UINT32_MAX;
    uint64_t audio_index = 0;
    int64_t wall_start_ms = 0;
    uint32_t audio_send_failures = 0;
    uint32_t audio_clock_resyncs = 0;
    bool audio_send_confirmed = false;

    while (atomic_load_explicit(&s_tasks_running, memory_order_acquire)) {
        uint32_t current_generation = tirtc_adapter_connection_generation();
        if (!tirtc_adapter_has_connection() ||
            !atomic_load_explicit(&s_uplink_active, memory_order_acquire) ||
            !tirtc_adapter_audio_uplink_ready()) {
            if (audio_source_is_open(&audio)) {
                close_audio_source(&audio);
            }
            generation = current_generation;
            vTaskDelay(pdMS_TO_TICKS(20));
            continue;
        }

        if (!audio_source_is_open(&audio) || generation != current_generation) {
            close_audio_source(&audio);
            if (!open_audio_asset(&audio)) {
                ESP_LOGE(TAG, "cannot open configured audio asset");
                vTaskDelay(pdMS_TO_TICKS(500));
                continue;
            }
            generation = current_generation;
            audio_index = 0;
            wall_start_ms = esp_timer_get_time() / 1000;
            audio_send_failures = 0;
            audio_clock_resyncs = 0;
            audio_send_confirmed = false;
            ESP_LOGI(TAG,
                     "audio sender started after transport readiness for connection generation=%lu",
                     (unsigned long)generation);
        }

        int64_t elapsed = esp_timer_get_time() / 1000 - wall_start_ms;
        uint64_t audio_pts = audio_index * s_config.audio.packet_ms;
        if (elapsed > (int64_t)(audio_pts + s_config.audio.packet_ms * 2U)) {
            int64_t lateness = elapsed - (int64_t)audio_pts;
            wall_start_ms += lateness;
            elapsed -= lateness;
            audio_clock_resyncs++;
            if (audio_clock_resyncs == 1U ||
                audio_clock_resyncs % 20U == 0U) {
                ESP_LOGW(TAG,
                         "audio pacing resynchronized count=%lu lateness=%lld ms",
                         (unsigned long)audio_clock_resyncs,
                         (long long)lateness);
            }
        }
        if ((int64_t)audio_pts > elapsed + 1) {
            uint64_t wait_ms = audio_pts - (uint64_t)elapsed;
            vTaskDelay(pdMS_TO_TICKS(wait_ms > 20U ? 20U : wait_ms));
            continue;
        }

        size_t size = 0;
        device_media_file_result_t result = next_audio_packet(
            &audio, audio_packet, sizeof(audio_packet), &size, true);
        if (result != DEVICE_MEDIA_FILE_OK) {
            ESP_LOGE(TAG, "audio read failed: %s",
                     device_media_file_result_name(result));
            (void)tirtc_adapter_disconnect();
            continue;
        }
        int rc = tirtc_adapter_send_audio(&s_config.audio,
                                           (uint32_t)audio_pts,
                                           audio_packet,
                                           (uint32_t)size);
        if (rc < 0) {
            audio_send_failures++;
            if (audio_send_failures == 1U ||
                audio_send_failures % 50U == 0U) {
                ESP_LOGW(TAG,
                         "audio send failed rc=%d count=%lu send-buffer=%u",
                         rc,
                         (unsigned long)audio_send_failures,
                         (unsigned)tirtc_adapter_send_buffer_used());
            }
        } else if (!audio_send_confirmed) {
            audio_send_confirmed = true;
            ESP_LOGI(TAG,
                     "audio uplink confirmed codec=%s packet=%u bytes duration=%lu ms",
                     device_audio_codec_name(s_config.audio.codec),
                     (unsigned)size,
                     (unsigned long)s_config.audio.packet_ms);
        }
        audio_index++;
    }

    close_audio_source(&audio);
    s_audio_task = NULL;
    vTaskDelete(NULL);
}

esp_err_t media_runtime_init(void)
{
    if (s_ready) {
        return ESP_OK;
    }
    esp_vfs_spiffs_conf_t mount = {
        .base_path = MEDIA_MOUNT_POINT,
        .partition_label = "media",
        .max_files = 5,
        .format_if_mount_failed = false,
    };
    esp_err_t err = esp_vfs_spiffs_register(&mount);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "SPIFFS mount failed: %s", esp_err_to_name(err));
        return err;
    }
    err = load_profile(&s_config);
    if (err == ESP_OK) {
        err = validate_assets();
    }
    if (err != ESP_OK) {
        esp_vfs_spiffs_unregister("media");
        return err;
    }
    s_ready = true;
    ESP_LOGI(TAG,
             "profile loaded: audio=%s; ESP32-S3 video=unsupported",
             s_config.audio.asset_path);
    return ESP_OK;
}

esp_err_t media_runtime_start(void)
{
    if (!s_ready) {
        return ESP_ERR_INVALID_STATE;
    }
    if (atomic_load_explicit(&s_tasks_running, memory_order_acquire)) {
        return ESP_OK;
    }
    atomic_store_explicit(&s_tasks_running, true, memory_order_release);
    BaseType_t audio_created = xTaskCreate(audio_sender_task,
                                           "audio_sender",
                                           6144,
                                           NULL,
                                           7,
                                           &s_audio_task);
    if (audio_created != pdPASS) {
        atomic_store_explicit(&s_tasks_running, false, memory_order_release);
        s_audio_task = NULL;
        return ESP_ERR_NO_MEM;
    }

    return ESP_OK;
}

void media_runtime_stop(void)
{
    atomic_store_explicit(&s_tasks_running, false, memory_order_release);
}

bool media_runtime_ready(void)
{
    return s_ready;
}

const device_media_config_t *media_runtime_config(void)
{
    return s_ready ? &s_config : NULL;
}

void media_runtime_set_uplink_active(bool active)
{
    atomic_store_explicit(&s_uplink_active, active, memory_order_release);
}

bool media_runtime_uplink_active(void)
{
    return atomic_load_explicit(&s_uplink_active, memory_order_acquire);
}

/*
 * 产品媒体接入层。
 *
 * 上行路径（由产品补齐）：麦克风/摄像头任务 -> 编码 -> starter_tirtc_send_*。
 * 下行路径（模板已搭好线程切换）：SDK 回调 -> 固定队列 -> audio_sink_task。
 *
 * 这里故意不提供 Flash 模拟媒体。不同开发板只修改本文件中的板级 TODO，
 * 不需要把 I2S、摄像头或编解码器细节带入会话状态机。
 */
#include "starter_media.h"

#include <stdatomic.h>
#include <string.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#define AUDIO_RX_BYTES 1500U
#define AUDIO_RX_QUEUE_DEPTH 8U

/* 队列项拥有 payload 副本，因此 SDK 回调返回后仍可安全消费。 */
typedef struct {
    starter_tirtc_mode_t mode;
    uint32_t generation;
    starter_tirtc_frame_t frame;
    uint8_t payload[AUDIO_RX_BYTES];
} audio_rx_item_t;

static const char *TAG = "starter_media";

/*
 * SDK 回调、会话任务和产品媒体任务会并发访问这些状态。原子变量用于读取
 * 瞬时快照；start/stop 的业务顺序仍由 starter_runtime 单任务保证。
 */
static atomic_bool s_ready;
static atomic_bool s_active;
static atomic_int s_mode;
static atomic_uint_fast32_t s_generation;
static atomic_uint_fast32_t s_audio_sent;
static atomic_uint_fast32_t s_video_sent;
static atomic_uint_fast32_t s_audio_received;
static atomic_uint_fast32_t s_audio_dropped;
static QueueHandle_t s_audio_rx_queue;

/* 同时匹配 mode 和 generation，避免上一条连接的迟到音频进入新会话。 */
static bool same_session(starter_tirtc_mode_t mode, uint32_t generation)
{
    return atomic_load_explicit(&s_active, memory_order_acquire) &&
           atomic_load_explicit(&s_mode, memory_order_acquire) == mode &&
           atomic_load_explicit(&s_generation, memory_order_acquire) == generation;
}

static void audio_sink_task(void *argument)
{
    (void)argument;
    audio_rx_item_t item;
    for (;;) {
        if (xQueueReceive(s_audio_rx_queue, &item, portMAX_DELAY) != pdTRUE) {
            continue;
        }

        /*
         * TODO(product-media-playback):
         * 1. 将 item.payload[0..item.frame.length) 的 G.711 A-law 解码成 PCM；
         * 2. 把 PCM 写入开发板 I2S/codec 扬声器；
         * 3. stop 或 generation 变化时丢弃硬件缓冲中的旧会话数据。
         *
         * 本任务已经离开 TiRTC 回调线程，允许执行有界的硬件等待；不要把
         * 解码和 I2S 写入移回 starter_tirtc 的 on_audio 回调。
         */
        (void)item;
    }
}

esp_err_t starter_media_init(void)
{
    if (atomic_load_explicit(&s_ready, memory_order_acquire)) {
        return ESP_OK;
    }
    /* 固定深度队列限制了弱网突发或扬声器阻塞时的内存占用。 */
    s_audio_rx_queue = xQueueCreate(AUDIO_RX_QUEUE_DEPTH, sizeof(audio_rx_item_t));
    if (s_audio_rx_queue == NULL) {
        return ESP_ERR_NO_MEM;
    }
    if (xTaskCreate(audio_sink_task, "product_audio_rx", 4096, NULL, 6, NULL) !=
        pdPASS) {
        vQueueDelete(s_audio_rx_queue);
        s_audio_rx_queue = NULL;
        return ESP_ERR_NO_MEM;
    }
    atomic_store_explicit(&s_ready, true, memory_order_release);
    ESP_LOGI(TAG, "media seam ready; no default camera, microphone, or speaker adapter");
    return ESP_OK;
}

esp_err_t starter_media_start(starter_tirtc_mode_t mode, uint32_t generation)
{
    if (!atomic_load_explicit(&s_ready, memory_order_acquire) ||
        generation == 0U ||
        (mode != STARTER_TIRTC_H5 && mode != STARTER_TIRTC_AI)) {
        return ESP_ERR_INVALID_STATE;
    }
    /* 新会话不能播放上一代连接残留在队列中的数据。 */
    if (s_audio_rx_queue != NULL) {
        xQueueReset(s_audio_rx_queue);
    }
    atomic_store_explicit(&s_audio_sent, 0, memory_order_release);
    atomic_store_explicit(&s_video_sent, 0, memory_order_release);
    atomic_store_explicit(&s_audio_received, 0, memory_order_release);
    atomic_store_explicit(&s_audio_dropped, 0, memory_order_release);
    atomic_store_explicit(&s_mode, mode, memory_order_release);
    atomic_store_explicit(&s_generation, generation, memory_order_release);
    atomic_store_explicit(&s_active, true, memory_order_release);

    /*
     * TODO(product-media-capture):
     * 1. 启动板级麦克风任务，把 PCM 编码为 G.711 A-law、8 kHz、单声道；
     * 2. starter_tirtc_audio_ready() 为 true 时调用 starter_tirtc_send_alaw()；
     * 3. H5 模式按板级合同从 MJPEG/H.264/H.265 中选一种，在 video_ready()
     *    为 true 时调用对应 starter_tirtc_send_*()；AI 模式禁止启动视频；
     * 4. 使用单调递增毫秒时间戳；MJPEG 每次发送完整 JPEG，H.264/H.265
     *    每次发送完整 Annex-B access unit；
     * 5. 发送成功后按需累加 s_audio_sent/s_video_sent 状态计数。
     *
     * 采集、编码和发送循环应属于板级任务，不要占用 SDK 回调线程。
     */
    ESP_LOGI(TAG,
             "session media requested mode=%d generation=%lu; product capture is not connected",
             (int)mode,
             (unsigned long)generation);
    return ESP_OK;
}

void starter_media_stop(void)
{
    /*
     * TODO(product-media-capture): 通知板级采集/编码任务退出，等待它们停止后
     * 再释放 DMA 缓冲和硬件句柄。任务必须观察 active/generation，不能在
     * stop 返回后继续向已经结束的连接发送帧。
     */
    atomic_store_explicit(&s_active, false, memory_order_release);
    atomic_store_explicit(&s_generation, 0, memory_order_release);
    if (s_audio_rx_queue != NULL) {
        xQueueReset(s_audio_rx_queue);
    }
}

void starter_media_request_key_frame(uint32_t generation)
{
    if (generation == 0U ||
        generation != atomic_load_explicit(&s_generation, memory_order_acquire)) {
        return;
    }
    /*
     * TODO(product-media-keyframe): H.264/H.265 编码器立即生成 IDR，并给下一
     * 个 access unit 传 key_frame=true；MJPEG 每帧独立，可忽略该请求。
     */
}

void starter_media_submit_audio(starter_tirtc_mode_t mode,
                                uint32_t generation,
                                const starter_tirtc_frame_t *frame,
                                const void *data)
{
    if (s_audio_rx_queue == NULL || frame == NULL || data == NULL ||
        frame->length == 0U || frame->length > AUDIO_RX_BYTES ||
        !same_session(mode, generation)) {
        atomic_fetch_add_explicit(&s_audio_dropped, 1, memory_order_relaxed);
        return;
    }
    /* data 由 SDK 持有，只在回调期间有效，所以必须在返回前复制。 */
    audio_rx_item_t item = {
        .mode = mode,
        .generation = generation,
        .frame = *frame,
    };
    memcpy(item.payload, data, frame->length);
    if (xQueueSend(s_audio_rx_queue, &item, 0) == pdTRUE) {
        atomic_fetch_add_explicit(&s_audio_received, 1, memory_order_relaxed);
    } else {
        atomic_fetch_add_explicit(&s_audio_dropped, 1, memory_order_relaxed);
    }
}

starter_media_status_t starter_media_status(void)
{
    return (starter_media_status_t) {
        .active = atomic_load_explicit(&s_active, memory_order_acquire),
        .mode = (starter_tirtc_mode_t)atomic_load_explicit(&s_mode,
                                                            memory_order_acquire),
        .generation = (uint32_t)atomic_load_explicit(&s_generation,
                                                      memory_order_acquire),
        .audio_sent = (uint32_t)atomic_load_explicit(&s_audio_sent,
                                                      memory_order_acquire),
        .video_sent = (uint32_t)atomic_load_explicit(&s_video_sent,
                                                      memory_order_acquire),
        .audio_received = (uint32_t)atomic_load_explicit(&s_audio_received,
                                                          memory_order_acquire),
        .audio_dropped = (uint32_t)atomic_load_explicit(&s_audio_dropped,
                                                         memory_order_acquire),
    };
}

#include "tirtc_bk_probe.h"

#include <driver/flash.h>
#include <driver/lcd.h>
#include <driver/tp.h>
#include <modules/chip_support.h>
#include <os/os.h>

#if CONFIG_SOC_BK7258
#define TIRTC_BK_SOC "BK7258"
#else
#error "this probe asset is for the BK7258 bk_avdk_smp v3.1.1 line"
#endif

__attribute__((weak)) const void *tirtc_bk_probe_active_lcd(void)
{
    return NULL;
}

__attribute__((weak)) bool tirtc_bk_probe_audio(tirtc_bk_audio_snapshot_t *out)
{
    (void)out;
    return false;
}

__attribute__((weak)) uint32_t tirtc_bk_probe_application_usable_bytes(void)
{
    return 0;
}

static const char *test_name(tirtc_bk_test_t value)
{
    switch (value) {
    case TIRTC_BK_TEST_PASS:
        return "pass";
    case TIRTC_BK_TEST_FAIL:
        return "fail";
    default:
        return "not_run";
    }
}

static void emit_endpoint(const tirtc_bk_audio_endpoint_t *endpoint)
{
    if (!endpoint->present) {
        os_printf("{\"state\":\"unknown\",\"method\":null,\"source\":null,"
                  "\"channels\":null,\"sample_rates_hz\":[],\"sample_bits\":[],"
                  "\"formats\":[],\"test\":\"not_run\"}");
        return;
    }
    os_printf("{\"state\":\"detected\",\"method\":\"board_audio_adapter\","
              "\"source\":\"pinned-bsp\",\"channels\":%u,"
              "\"sample_rates_hz\":[%u],\"sample_bits\":[%u],"
              "\"formats\":[\"pcm_s16le\"],\"test\":\"%s\"}",
              endpoint->channels, (unsigned)endpoint->sample_rate_hz,
              endpoint->sample_bits, test_name(endpoint->test));
}

void tirtc_bk_probe_emit(void)
{
    const lcd_device_t *lcd = (const lcd_device_t *)tirtc_bk_probe_active_lcd();
    tp_device_t *tp = bk_tp_get_device();
    tirtc_bk_audio_snapshot_t audio = {0};
    bool has_audio = tirtc_bk_probe_audio(&audio);
    uint32_t app_bytes = tirtc_bk_probe_application_usable_bytes();

    os_printf("TIRTC_BK_PROBE {");
    os_printf("\"schema_version\":1,\"artifact_sha256\":null,");
    os_printf("\"identity\":{\"soc\":\"%s\",\"chip_revision\":\"%u\","
              "\"board_model\":null,\"pcb_revision\":null,"
              "\"sdk\":{\"name\":\"bk_avdk_smp\",\"version\":null,"
              "\"revision\":null},\"board_config_sha256\":null},",
              TIRTC_BK_SOC, (unsigned)bk_get_hardware_chip_id_version());
    os_printf("\"flash\":{\"state\":\"measured\","
              "\"method\":\"bk_flash_get_id/current_total_size\","
              "\"source\":\"runtime\",\"jedec_id\":\"0x%08x\","
              "\"recognized\":null,\"physical_bytes\":null,"
              "\"mapped_bytes\":%u,\"application_usable_bytes\":",
              (unsigned)bk_flash_get_id(),
              (unsigned)bk_flash_get_current_total_size());
    if (app_bytes) {
        os_printf("%u},", (unsigned)app_bytes);
    } else {
        os_printf("null},");
    }
    os_printf("\"memory\":{\"internal_sram\":{\"state\":\"measured\","
              "\"total_bytes\":%u,\"free_boot_bytes\":%u,"
              "\"minimum_free_bytes\":%u,\"largest_free_block_bytes\":null},",
              (unsigned)rtos_get_total_heap_size(),
              (unsigned)rtos_get_free_heap_size(),
              (unsigned)rtos_get_minimum_free_heap_size());
    os_printf("\"psram\":{\"state\":\"measured\",\"present\":%s,"
              "\"total_bytes\":%u,\"free_boot_bytes\":%u,"
              "\"minimum_free_bytes\":%u,\"largest_free_block_bytes\":null}},",
              rtos_get_psram_total_heap_size() ? "true" : "false",
              (unsigned)rtos_get_psram_total_heap_size(),
              (unsigned)rtos_get_psram_free_heap_size(),
              (unsigned)rtos_get_psram_minimum_free_heap_size());

    if (lcd) {
        os_printf("\"display\":{\"state\":\"detected\","
                  "\"method\":\"active-board-lcd\",\"source\":\"pinned-bsp\","
                  "\"controller\":null,\"bus\":null,\"width_px\":%u,"
                  "\"height_px\":%u,\"width_mm\":null,\"height_mm\":null,"
                  "\"pixel_format\":null,\"test\":\"not_run\"},",
                  lcd->width, lcd->height);
    } else {
        os_printf("\"display\":{\"state\":\"unknown\",\"method\":null,"
                  "\"source\":null,\"controller\":null,\"bus\":null,"
                  "\"width_px\":null,\"height_px\":null,\"width_mm\":null,"
                  "\"height_mm\":null,\"pixel_format\":null,"
                  "\"test\":\"not_run\"},");
    }

    if (tp) {
        os_printf("\"touch\":{\"state\":\"detected\","
                  "\"method\":\"bk_tp_get_device\",\"source\":\"runtime\","
                  "\"controller\":null,\"bus\":\"i2c\",\"points\":%u,"
                  "\"test\":\"not_run\"},", tp->tp_num);
    } else {
        os_printf("\"touch\":{\"state\":\"unknown\",\"method\":null,"
                  "\"source\":null,\"controller\":null,\"bus\":null,"
                  "\"points\":null,\"test\":\"not_run\"},");
    }

    os_printf("\"camera\":{\"state\":\"unknown\",\"method\":null,"
              "\"source\":null,\"sensor\":null,\"output_profiles\":[],"
              "\"test\":\"not_run\"},\"audio\":{\"microphone\":");
    emit_endpoint(&audio.microphone);
    os_printf(",\"speaker\":");
    emit_endpoint(&audio.speaker);
    if (has_audio) {
        os_printf(",\"duplex\":{\"simultaneous\":%s,\"playback_reference\":%s,"
                  "\"aec_available\":%s,\"aec_test\":\"%s\"}},",
                  audio.simultaneous ? "true" : "false",
                  audio.playback_reference ? "true" : "false",
                  audio.aec_available ? "true" : "false",
                  test_name(audio.aec_test));
    } else {
        os_printf(",\"duplex\":{\"simultaneous\":null,"
                  "\"playback_reference\":null,\"aec_available\":null,"
                  "\"aec_test\":\"not_run\"}},");
    }
    os_printf("\"controls\":{\"verified_buttons\":0,"
              "\"intent_map_approved\":false},\"integration\":{"
              "\"tirtc_sdk_compatible\":null,\"audio_uplink_pipeline\":null,"
              "\"audio_downlink_pipeline\":null,\"video_uplink_pipeline\":null,"
              "\"session_arbiter\":null,\"device_call_protocol\":null,"
              "\"wechat_voip_protocol\":null},\"requested_features\":[],"
              "\"issues\":[]}\r\n");
}

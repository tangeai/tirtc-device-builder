#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    TIRTC_BK_TEST_NOT_RUN = 0,
    TIRTC_BK_TEST_PASS,
    TIRTC_BK_TEST_FAIL,
} tirtc_bk_test_t;

typedef struct {
    bool present;
    uint8_t channels;
    uint32_t sample_rate_hz;
    uint8_t sample_bits;
    tirtc_bk_test_t test;
} tirtc_bk_audio_endpoint_t;

typedef struct {
    tirtc_bk_audio_endpoint_t microphone;
    tirtc_bk_audio_endpoint_t speaker;
    bool simultaneous;
    bool playback_reference;
    bool aec_available;
    tirtc_bk_test_t aec_test;
} tirtc_bk_audio_snapshot_t;

/* Override these weak hooks in the exact board project. Returning NULL/false
 * preserves unknown rather than claiming that a peripheral is absent. */
const void *tirtc_bk_probe_active_lcd(void);
bool tirtc_bk_probe_audio(tirtc_bk_audio_snapshot_t *out);
uint32_t tirtc_bk_probe_application_usable_bytes(void);

/* Run after board peripheral initialization. Active speaker/touch tests remain
 * explicit board commands; this snapshot never plays audio or writes Flash. */
void tirtc_bk_probe_emit(void);

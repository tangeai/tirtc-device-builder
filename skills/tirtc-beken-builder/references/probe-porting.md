# Probe porting contract

Use this reference when adding the on-device diagnostic task to a pinned Beken
SDK/BSP project.

## SDK baseline

For BK7258 multimedia work, start with Beken's official Gitee `bk_avdk_smp`
tag `release/v3.1.1.8`, commit
`1cfd56af09a3cb6470f35f1e0c604035ed1b6ee7`. Do not substitute the locally
delivered `3.1.1.8-20260605` tree: it contains product/private modifications and
is reference evidence only. Keep an upper-layer solution and SDK on matching
tags. Confirm BK7259 against its own published support matrix and release line
rather than assuming BK7258 compatibility.

## Output contract

Emit exactly one UTF-8 JSON object on a single log line:

```text
TIRTC_BK_PROBE {"schema_version":1,...}
```

Start from `assets/probe-report.example.json`. Preserve `null` for unknown
values. Each peripheral has `state`, `method`, `source`, and `test`. Active test
values are `pass`, `fail`, or `not_run`. Do not put secrets, MAC addresses, SSIDs
or captured audio in the report.

The final firmware must expose the same probe through a development-only shell
command or build option. Disable active speaker/touch tests in unattended
production boot.

## Adapter seam

Implement these operations using symbols present in the pinned SDK checkout;
names vary across Armino/BK-IDK branches, so discover them with source search:

```c
struct tirtc_bk_probe_ops {
    int (*read_soc)(struct probe_soc *out);
    int (*read_flash)(struct probe_flash *out);
    int (*read_memory)(struct probe_memory *out);
    int (*inspect_display)(struct probe_display *out);
    int (*test_display)(struct probe_display_test *out);
    int (*inspect_touch)(struct probe_touch *out);
    int (*test_touch)(struct probe_touch_test *out);
    int (*inspect_audio)(struct probe_audio *out);
    int (*test_capture)(struct probe_capture_test *out);
    int (*test_playback)(struct probe_playback_test *out);
    int (*test_duplex_aec)(struct probe_duplex_test *out);
};
```

For `bk_avdk_smp` v3.1.1, copy
`assets/bk-avdk-smp-v3.1.1/tirtc_bk_probe.[ch]` into an AP component. It already
implements the read-only chip/Flash/heap/PSRAM snapshot and structured output.
Override its three weak board hooks to provide the active LCD, audio snapshot
and usable application-partition bytes. The asset intentionally leaves active
LCD, touch and audio tests for board-specific commands because those tests need
known routing and human-safe output control.

This supplied component targets BK7258 only. For BK7259, use the same JSON
contract and hooks but implement a separate adapter against the pinned v4.0.1
headers; v4 panel registration/read-ID APIs and SoC paths are not assumed to be
source-compatible with the v3.1.1 asset.

The orchestrator owns ordering, time bounds, JSON encoding and redaction. The
adapter owns SDK calls, board pins, controller identities and DMA constraints.
Return `unsupported` for an authoritative absence and `unknown` for a missing
implementation or unsafe test; those are materially different outcomes.

## Source discovery

Search the selected checkout for its actual equivalents of:

- chip/revision and reset-reason getters;
- Flash device/JEDEC/size and partition-table APIs;
- heap total/free/minimum/largest-block statistics, including PSRAM regions;
- LCD device registration, panel init, resolution and frame-buffer APIs;
- touch controller registration/read-ID/coordinate APIs;
- audio codec, ADC/DAC, I2S/SAI, DMA, AEC and audio-pipeline examples.

For BK7258, compare the official `rgb_lcd_example`, `player_service_example`,
LVGL projects and product solutions in `bk_avdk_smp`; compile the smallest
working vendor example before adding one probe operation at a time. Record the
SDK commit and board configuration hash in the output.

### Confirmed v3.1.1 source map

The following symbols were verified in official `bk_avdk_smp` revision
`993df5647f084551a677a2bc741b200cfd75d5f2`. Recheck them after changing tags:

| Probe | API or structure | Source path |
|---|---|---|
| silicon revision | `bk_get_hardware_chip_id_version()` | `ap/include/modules/chip_support.h` |
| Flash identity/capacity | `bk_flash_get_id()`, `bk_flash_get_current_total_size()` | `ap/include/driver/flash.h` |
| usable partitions | `bk_flash_partition_get_info()` | `ap/include/driver/flash_partition.h` |
| internal heap | `rtos_get_total_heap_size()`, `rtos_get_free_heap_size()`, `rtos_get_minimum_free_heap_size()` | `ap/include/os/os.h` |
| PSRAM heap | `rtos_get_psram_total_heap_size()`, `rtos_get_psram_free_heap_size()`, `rtos_get_psram_minimum_free_heap_size()` | `ap/include/os/os.h` |
| compiled LCD profiles | `get_lcd_devices_list()`, `get_lcd_devices_num()`, `lcd_device_t.width/height` | `ap/include/driver/lcd.h`, `ap/include/driver/lcd_types.h` |
| touch detection | `bk_tp_driver_init()`, `bk_tp_get_device()` | `ap/include/driver/tp.h` |
| analog audio | `bk_aud_adc_*`, `bk_aud_dac_*` | `ap/include/driver/aud*.h` |
| duplex/AEC reference | `bk_voice_service` configuration and validation | `ap/components/bk_voice_service/src/bk_voice_service.c` |

`get_lcd_devices_list()` enumerates compiled profiles, not fitted hardware.
`bk_tp_get_device()` becomes meaningful only after the BSP's constrained sensor
list and pins are configured and `bk_tp_driver_init()` succeeds. The v3.1.1
voice service confirms that enabled software AEC consumes a speaker-output
reference ring buffer, while hardware AEC has channel/reference-mode constraints;
an `aec_en` flag alone is therefore insufficient evidence.

## Active test bounds

- Restore the prior display contents when practical.
- Require a button/shell confirmation before speaker playback; cap duration and
  start at a conservative level.
- Store only audio statistics, never raw samples, unless the user explicitly
  requests and authorizes capture.
- Time-bound every driver call and restore GPIO/power/clock state on failure.
- Use a scratch data partition explicitly reserved for destructive Flash tests;
  capacity detection itself remains read-only.

## Collection

Capture serial output with the board vendor's monitor, then run:

```bash
python3 <skill-dir>/scripts/bk_probe_report.py collect board.log probe-report.json
```

The collector selects the last complete framed report, validates it, and writes
formatted JSON. Keep the raw log only when it has been checked for secrets.

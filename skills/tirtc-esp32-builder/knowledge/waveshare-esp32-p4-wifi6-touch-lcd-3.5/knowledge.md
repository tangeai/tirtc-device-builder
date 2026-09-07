# Waveshare ESP32-P4-WIFI6-Touch-LCD-3.5

2026-09-07. Knowledge only; PCB and silicon revisions unresolved. This package
contains source-correlated observations and targeted regressions, not an
installable adapter or complete Hardware IR. A matching sales name does not
authorize pin reuse. No credentials, raw call logs or user media are retained.

## Read only the needed source

| Baseline | Pinned source | Locate next |
| --- | --- | --- |
| Product business | xiaotai, baseline `8d67f0fe1b7385485e9d3de57065be53d10639ed` plus uncommitted P4 port | `lckfb-szpi-esp32s3-tirtc/components/starter_runtime/src/starter_runtime.c`, shared `starter_product`, `starter_tirtc` |
| Hardware/media | tirtc-device-example `cad4cbe58c3ff451906322930ceede19e6bf6a07`, app 1.5.3 | `complete-applications/esp32-p4/device-monitor/main/` |
| Vendor | waveshareteam/ESP32-P4-WIFI6-Touch-LCD-3.5 `870588e62daaf723f3c52f0060d8dc053665ed30` | `examples/esp-idf/06_I2SCodec`, `docs/revisions.md`, schematic |
| Cross-check | xiaozhi-esp32 `1ce658bcb9ce9aac69d3f87af9894a715b7175f6` | `main/boards/waveshare/esp32-p4-wifi6-touch-lcd-3.5/` |

Source paths are repository-relative, not prerequisites for a particular home
directory. Product HEAD alone does not identify dirty source; retain the local
diff and BIN/ELF identity when promoting this package. Project source maps live
under `docs/boards/waveshare-esp32-p4-wifi6-touch-lcd-3.5/`; current build status
is in `waveshare-esp32p4-xiaotai/PORT_STATUS.md` and `BUILD_IDENTITY.md`.

## Hardware candidates (source-correlated, re-probe on new hardware)

- P4, 32 MiB PSRAM, 16 MiB flash; ESP32-C6 over Hosted SDIO. P4 requires its own
  RISC-V SDK; the tested IDF is 5.5.4-dirty, TiRTC 2.3.0.
- ST7796 **SPI**, physical 320x480 / landscape 480x320; FT6336 uses the FT5x06
  driver family. CSI camera does not imply a DSI display.
- No onboard IMU is documented for this model: vendor hardware inventory omits
  one, pinned monitor BSP declares `BSP_CAPS_IMU=0`, and vendor BSP 2.0.1 lists
  IMU unavailable. External sensing is needed for motion-based rotation; BSP
  support flags alone are not proof of hardware absence. Sources checked
  2026-09-07: https://docs.waveshare.com/ESP32-P4-WIFI6-Touch-LCD-3.5 and
  https://components.espressif.com/components/waveshare/esp32_p4_wifi6_touch_lcd_3_5/versions/2.0.1/readme
- Shared I2C1 SDA7/SCL8: pass the existing bus to camera SCCB (`init_sccb=false`),
  codec and touch; an unused I2C0 macro is not evidence for a second owner.
- ES8311 I2S1 MCLK13/BCLK12/WS10/DOUT9/DIN11; PA53 high. Shared TX/RX,
  16 kHz stereo 16-bit, left MIC/right DAC reference. Monitor uses
  `.no_dac_ref=false`, codec register 0x44=0x58. Validate reference energy and
  double-talk; a board-level reference macro in Xiaozhi does not prove its
  actual codec object enables reference input.
- LCD MOSI20/CLK21/CS23/DC26/RST27/BL28; touch RST29/INT50; BOOT35.
  Verify combined rotation/mirror and all four touch corners. BOOT is distinct
  from AXP2101 power controls; PMIC power sequencing remains unverified.
- C6 SDIO CLK18/CMD19/D0..3=14..17/RST54. Read host/slave versions; STA working
  does not verify SoftAP/captive portal. Read the remote STA MAC after got-IP.
- OV5647 source: `main/drivers/camera/camera_driver.c`. Sensor mode may run
  faster than requested output: observed 800x640@50 sensor paced to 15 fps.
  Verify PID and actual silicon revision before selecting rev<3 defaults.

## Media and failures worth remembering

| Symptom | Evidence and correction | Regression / next source |
| --- | --- | --- |
| VoIP audio but no remote image | Callback metadata stream=1/media=65 (JPEG), rx=37 and decoded=0; adapter only allowed stream11. Receive by active connection/generation/codec, not uplink ID. User later reported image visible. | P4 `tools/test_video_ingress.py`, actual `p4_video_submit`/`drain_video`; monitor `tirtc_session_on_video` |
| Remote producer not requested | Monitor subscribes then sends its version-specific video-enable command `(SN<<16)\u007c0x1105`, byte1. Added missing request, but this alone was not proven to fix image. | `tools/test_p4_video.py`; monitor `tirtc_session.c`, `tirtc_commands.c` |
| H264 open fails with >8 MiB free | Singleton output workspace remained reserved for old profile. Stop worker, apply profile, reconcile reservation, restart. | `tools/test_p4_profile_switch.py`; `camera_pipeline_on_rtc_video_config_changed` |
| Repeated WHIP attempts leak | Shared worker used WithCaps creation and ordinary deletion. Fixed to paired deletion; 24 KiB stack plus TCB per completed attempt was retained. | S3 `tools/test_voip_task_cleanup.py`; installed IDF `esp_additions/idf_additions.c` |
| UI slow / video not smooth | Product UI tick100ms limits presentation near10fps; renderer input24x256KiB plus output20x480x320x2 dominate pools. Retained pools are intentional, not proven optimal for this product. | `call_video_renderer_config.h`, `p4_video_ui_tick`; measure before tuning |

Product-specific media: device CALL H264 both directions; WeChat VOIP H264 up /
MJPEG down, profile video enabled with 640x480, 8k mono A-law. Preserve explicit
voice calls. Camera privacy disables local capture/send while keeping remote
decode/audio; microphone is independent. Profile declaration is not proof of
actual packets or display. P4 H264 encode is hardware; downstream H264 here is
software, MJPEG uses hardware JPEG plus scaling.

## Evidence boundary

P4 `xiaotai-p4-voip.8` compiled with host regressions including 100 simulated
worker exits; no repeated-call heap HIL yet.

- BIN SHA256: `8bb2e46f3ce68318ebdd544c6cff979e6885e1c40b70ff0ee1731342b07c55e1`
- ELF SHA256: `6a138dede2fe20e7980937801c48a0206b0a78a3634a49a9ef3e31f9bce811aa`
- P4 SDK archive SHA256: `a7a01ffd496a55364c7e4d665ff3884d078147bba96752a965d97befca12e451`

These identify historical local artifacts, not bundled binaries or a reproducible
release. User reports video visible after the stream-filter correction, without
a complete artifact-bound capture. Startup logs prove one successful media
start, not long-run stability. Earlier HMAC signing -> invalid LVGL event crash
is unresolved; no claim it was fixed by task cleanup. AEC/double-talk, weak
network, repeated calls, PMIC controls and full product parity remain pending.
Promote only after exact identity, portable adapter/IR/contracts and per-flow
artifact-bound acceptance are retained.

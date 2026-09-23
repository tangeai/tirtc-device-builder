# Waveshare ESP32-P4-WIFI6-Touch-LCD-4.3-C V1.0

Knowledge only. Exact board declared as Waveshare SKU 33875, PCB V1.0, with
OV5647 installed. The verified product artifact is XiaoTai `43c-port.10`, built
with ESP-IDF 5.5.4 and the TiRTC P4 2.3.0 validation archive. This package
records board and component lessons; it does not ship an adapter or authorize
reuse on another 4.3-inch revision.

## Hardware facts

- ESP32-P4NRW32 with 32 MiB PSRAM, 32 MiB flash and ESP32-C6-MINI-1-N4 Hosted
  Wi-Fi over SDIO (CLK18/CMD19/D0..3=14..17/RST54).
- ST7701 MIPI-DSI, two lanes at 500 Mbps, native portrait 480x800, RGB565,
  DPI 30 MHz, DSI PHY LDO_VO3 at 2.5 V, backlight GPIO26 inverted and reset27.
- GT911 at I2C 0x5D, native portrait coordinates, RST/INT not connected; polling
  worked. OV5647 CSI two-lane PID 0x5647 shares I2C1 SDA7/SCL8.
- ES8311 DAC at 7-bit 0x18 and ES7210 ADC at **7-bit 0x40**, PA GPIO53. Both
  share I2S1 MCLK13/BCLK12/WS10/DOUT9/DIN11. The codec abstraction used by this
  port accepts the ES7210 control address in 8-bit form, so pass `0x40 << 1`.
- ES7210 serial order is CH1/CH3/CH2/CH4. The selected compact DMA pair is
  `[MIC3 playback reference, MIC2 onboard microphone]`; swap it to the AEC
  contract `[microphone, reference]`. ES8311 OUTN is physically fed to MIC3.
- Product key K2 is GPIO23. K1/POWER GPIO21 participates in the PMIC/power path
  and needs separate short/long-press HIL; BOOT is GPIO35.

## Display failures and resolution

The ST7701 is a RAM-less video panel. Panel `swap_xy` is unavailable, so the
working product path exposes physical 480x800 to LVGL 8.3, sets `sw_rotate=1`,
and selects `LV_DISP_ROT_90` for the tested enclosure. GT911 reports native
coordinates and LVGL applies the same rotation to touch.

Observed traps:

| Symptom | Cause | Correction |
| --- | --- | --- |
| Horizontal tear lines | Dirty rectangles copied into the framebuffer being scanned | Compose only in a safe back buffer and request presentation at the DSI frame boundary |
| Flicker or local UI corruption after double buffering | Alternating buffers contained different generations because only current dirty regions were updated | After flip completion, copy the presented frame's damage into the recycled back buffer before the next LVGL refresh |
| Startup tear | Code assumed fb0 was the back buffer while DPI initially scanned fb0 | Initialize equal buffers with the backlight off and compose the first frame in fb1 |
| Portrait/garbled output | LVGL 8.3 90/270 rotation configured without `sw_rotate=1` | Enable software rotation before setting the display rotation |
| Dark blue rendered yellow/brown | `LV_COLOR_16_SWAP=y` data reached a natural-endian RGB565 DSI input | Byte-swap each RGB565 word once while composing the panel framebuffer |
| UI did not fill 800x480 | Shared product helpers scaled a 320x240 design grid using fixed predecessor dimensions | Use runtime logical display width/height in position, zoom, video viewport and pool sizing |
| Touch opposite to UI | Display rotation changed independently of touch mapping | Keep GT911 native coordinates and let LVGL rotate both display and pointer |

`lvgl_port` avoid-tearing did not solve this composition because software
rotation flushed through temporary non-framebuffer-resident chunks. A PPA
transpose experiment introduced separate direction/color uncertainty. These
failed experiments are diagnostic history, not preferred implementations.

## Evidence boundary

User HIL on 2026-09-23 reported UI and video normal with `43c-port.10` after the
ROT_90 and damage carry-forward correction. This establishes the board display
path for that artifact, not AEC double-talk, weak-network recovery, PMIC power
semantics or 24-hour stability.

- Application BIN SHA256:
  `2fb05d6985401b061ef3778f69b2f2b68a3d43cb6e7af145484d136de1ae2562`
- ELF SHA256:
  `38b1ce6f0a5455fbd658b1c5e5275b89a07f2d5a7561652cfac04a5b3e6368de`
- Local source evidence at capture time:
  `waveshare-esp32p4-4.3c-xiaotai/`, its Hardware IR, display driver, audio
  contract and `docs/ESP32-P4-WIFI6-Touch-LCD-4.3-C-移植诊断手册.md`.

Apply the general display invariants from
[display-pipeline.md](../../references/display-pipeline.md) to other panels.
Treat the GPIO, rotation, codec address, TDM slots and AEC wiring above as exact
board facts only.

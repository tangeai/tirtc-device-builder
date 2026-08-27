# Capability rules

Run `hardware_ir.py assess --strict` before generation. The script applies the minimum current starter contract; use this reference when explaining or extending the result.

## Current starter contract

| Feature | Required hardware/media path |
|---|---|
| `h5_live_audio` | Microphone path that produces G.711 A-law, 8 kHz, mono for stream 10 |
| `h5_live_video` | Camera plus H.264 Annex-B access units, SPS/PPS and IDR, and key-frame request control for stream 11 |
| `h5_talkback` | G.711 A-law, 8 kHz downlink decode and speaker path for stream 14 |
| `ai_talk` | A-law 8 kHz microphone and speaker paths for AI stream 1, started only after `start_session` succeeds |

The complete media path must be at least `corroborated` to become `READY_TO_PORT`. A path with unknown facts is `NEEDS_CONFIRMATION`; a confirmed missing or incompatible resource is `BLOCKED`. Only an end-to-end board run becomes `HIL_VERIFIED`.

## Non-negotiable checks

- Match the TiRTC precompiled SDK platform to the ESP-IDF target and its `manifest/build-contract.env` to the generated configuration.
- Keep H5 stream IDs and formats stable unless the user explicitly authorizes a coordinated public contract change across the server and all consumers.
- Start AI media only after the successful `start_session` response, and stop/flush media before disconnecting the session.
- Copy SDK callback payloads into bounded queues before returning. Perform decoding, playback, HTTP, and lifecycle changes outside SDK callbacks.
- Use monotonic timestamps and session generation to reject stale frames and delayed callbacks.

## Typical blocked cases

- A camera outputs JPEG but no evidenced H.264 encoder produces Annex-B access units.
- The board has a microphone but no encoder path for the required A-law sample rate.
- The board has a codec but its playback pins, clock, amplifier enable, or BSP driver remain unknown.
- A generic ESP32-S3 module is named without the carrier board that defines camera/audio wiring.
- The available TiRTC archive targets another chip, ESP-IDF ABI, or FreeRTOS configuration.

When a blocked case would require changing the H5 contract, replacing hardware, or obtaining a new TiRTC SDK build, report those alternatives instead of silently changing the project.

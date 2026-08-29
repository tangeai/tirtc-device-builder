# Capability rules

Run `hardware_ir.py assess --phase intake --strict` before generation. Hardware IR v2 validates the selected product contract rather than assuming one video codec or provisioning method. Schema v1 remains readable for existing H.264 projects.

## Current starter contract

| Feature | Required hardware/media path |
|---|---|
| `h5_live_audio` | Microphone path producing G.711 A-law, 8 kHz, mono for stream 10; audio controller/channel ownership and memory budget resolved |
| `h5_live_video` | Camera plus the selected MJPEG, H.264, or H.265 profile for stream 11; refresh/key-frame control, realtime pipeline, and memory budget resolved |
| `h5_talkback` | G.711 A-law, 8 kHz downlink decode and speaker path for stream 14; audio controller/GPIO ownership and memory budget resolved |
| `ai_talk` | A-law 8 kHz microphone and speaker paths for AI stream 1, started only after `start_session`; audio ownership/channel mapping and memory budget resolved |

Hardware identity, wiring, the selected media contract, and the adapter/resource design must be at least `corroborated` to become `READY_TO_PORT`. At intake, `available=true` means a pinned source path can implement the selected profile; it does not claim that the final adapter or physical media path has run. Implementation composition, final ELF policy, runtime memory margin, browser media, and stability belong to the build or HIL phases.

A design fact that is still unknown is `NEEDS_CONFIRMATION`; a confirmed missing or incompatible resource is `BLOCKED`. Facts that can be resolved safely through source inspection, adapter implementation, compilation, or post-link inspection should be resolved in that layer rather than converted into a request for HIL evidence.

## Selected video profiles

The current platform/Web contract supports all three profiles below on video stream 11. Hardware IR v2 separately stores the profiles the board can produce and exactly one selected profile for H5 video:

| Codec | Required output contract |
|---|---|
| `mjpeg` | `jpeg_complete_frames`: one complete JPEG per send; each frame independently refreshable |
| `h264` | `h264_annex_b_access_units`: Annex-B access units with SPS/PPS and IDR request behavior |
| `h265` | `h265_annex_b_access_units`: Annex-B access units with parameter-set and refresh behavior defined by the coordinated H5 contract |

Available but unselected board profiles do not satisfy or block the selected contract. A board may select MJPEG even though the platform also accepts H.264 and H.265. Stream IDs and codec support must be verified against the project-local platform contract rather than inferred from board hardware.

## Phased project gates

The intake phase requires:

- one selected and evidenced I2C driver-family plan when I2C is used;
- a selected Wi-Fi credential method that is available, reprovisionable, and keeps credentials outside source control;
- one evidenced binding method—verification code, factory-bound identity, development credentials, or documented custom flow—plus stored-binding behavior and reset control;
- feature-specific I2S/GPIO ownership plans, channel/TDM mapping, realtime camera policy, and a static startup/media memory budget.

At intake, `corroborated` on these fields means the design is resolved from authoritative sources and is safe to implement. After compilation, promote a field to `build_verified` only when the generated source, component lock, semantic gate, compile result, or post-link gate establishes it. Build assessment reruns the applicable project-relative [audio contract](audio-contract.md), [video contract](video-contract.md), and mandatory [runtime contract](runtime-contract.md); self-declared `resolved=true`, `pipeline_safe=true`, or memory-budget booleans cannot replace them. The build phase requires an exact on-disk artifact SHA-256 and returns `BUILD_VERIFIED` only when every requested feature passes. Runtime measurements never need to be invented to pass intake or build.

SoftAP is one Wi-Fi option, not a universal requirement. BLE, SmartConfig, factory NVS, development configuration, or a documented custom method can satisfy intake when the selected path is evidenced. Committed plaintext credentials are always `BLOCKED`.

## Non-negotiable runtime checks

- Match the TiRTC precompiled SDK platform to the ESP-IDF target and its `manifest/build-contract.env` to the generated configuration.
- Keep H5 stream IDs and formats stable unless the user explicitly authorizes a coordinated contract change across the server and consumers.
- Start AI media only after the successful `start_session` response; stop and flush media before disconnecting.
- Copy SDK callback payloads into bounded queues before returning. Perform decoding, playback, HTTP, and lifecycle changes outside callbacks.
- Use monotonic timestamps and session generation to reject stale frames and delayed callbacks.
- Record runtime evidence with the exact BIN/ELF SHA-256. Use `assess --phase hil --artifact-sha256 <sha>`; documentation verification alone never becomes v2 `HIL_VERIFIED`.

## Typical blocked cases

- The selected MJPEG/H.264/H.265 profile lacks its required output or refresh semantics.
- Audio hardware exists, but the A-law path, physical channel/TDM slot, clock, amplifier, or resource ownership is unresolved.
- Third-party components introduce both legacy and new ESP-IDF I2C drivers.
- A generic ESP32-S3 module is named without the carrier board wiring and hardware revision.
- Wi-Fi credentials are embedded in tracked source, or no available/reprovisionable credential path is selected.
- The TiRTC archive targets another chip, ESP-IDF ABI, or FreeRTOS configuration.

When a blocked case requires changing a public contract, replacing hardware, obtaining a new SDK, or choosing a provisioning policy, report alternatives instead of silently changing the project.

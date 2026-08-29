# TiRTC Porting Report

## Target

- Board ID: `{{BOARD_ID}}`
- Model/revision: `{{BOARD_MODEL_REVISION}}`
- Requested features: `{{REQUESTED_FEATURES}}`
- Selected media profile: `{{SELECTED_MEDIA_PROFILE}}`
- Selected Wi-Fi credential method: `{{SELECTED_WIFI_METHOD}}`
- Selected device-binding method: `{{SELECTED_BINDING_METHOD}}`
- Output project: `{{PROJECT_PATH}}`

## Locked inputs

| Input | Version/revision | Source or SHA-256 |
|---|---|---|
| Hardware IR |  |  |
| ESP-IDF |  |  |
| TiRTC SDK |  |  |
| BSP/board adapter |  |  |

## Capability assessment

| Feature | Status | Evidence or blocker |
|---|---|---|
| H5 live audio |  |  |
| H5 live video |  |  |
| H5 talkback |  |  |
| AI intercom |  |  |

## Semantic build gates

- Platform/Web video profiles: `{{PLATFORM_VIDEO_PROFILES}}`
- Board-selected video profile: `{{BOARD_VIDEO_PROFILE}}`
- Runtime contract path/SHA-256: `{{RUNTIME_CONTRACT}}`
- Endpoint/callback/downlink/AI-session result: `{{RUNTIME_GATE}}`
- Audio contract path/SHA-256: `{{AUDIO_CONTRACT}}`
- Codec clock-table result: `{{AUDIO_CLOCK_GATE}}`
- I2S mode/controller/slot/handoff result: `{{AUDIO_TOPOLOGY_GATE}}`
- Video contract path/SHA-256: `{{VIDEO_CONTRACT}}`
- Camera lock/PID/CPU/frame/backpressure result: `{{VIDEO_GATE}}`
- Final ELF I2C driver-family result: `{{I2C_ELF_GATE}}`
- Build artifact present in Hardware IR evidence: `{{BUILD_ARTIFACT_BINDING}}`
- Compiler result versus requested-feature result: `{{COMPILE_VS_CAPABILITY}}`

## Acceptance

| Level | PASS/FAIL/SKIP | Command and evidence |
|---|---|---|
| L-1 Environment |  |  |
| L0 Generate |  |  |
| L1 Build |  |  |
| L2 Boot |  |  |
| L3 Online |  |  |
| L4 Media |  |  |
| L5 H5 |  |  |
| L6 AI |  |  |
| L7 Stability |  |  |

## Firmware and flash record

- Serial port/chip: `{{SERIAL_TARGET}}`
- Project-relative firmware artifacts: `{{FIRMWARE_ARTIFACTS}}`
- Firmware SHA-256: `{{FIRMWARE_SHA256}}`
- Flash command/result: `{{FLASH_RESULT}}`

## Artifact-bound runtime evidence

| Artifact SHA-256 | Acceptance levels | Observations | Current/superseded |
|---|---|---|---|
|  |  |  |  |

## Runtime metrics

- Wi-Fi BSSID/channel/RSSI and roaming: `{{WIFI_RUNTIME_METRICS}}`
- Media tx/rx/drop/error and queue watermarks: `{{MEDIA_RUNTIME_METRICS}}`
- Camera overflow, internal heap/largest block, PSRAM: `{{RESOURCE_RUNTIME_METRICS}}`

## Remaining work and risks

`{{REMAINING_WORK}}`

## Sanitization

Logs and artifacts were checked for device keys, Wi-Fi passwords, complete MQTT/WHIP tokens, and user media: `{{SANITIZATION_RESULT}}`.

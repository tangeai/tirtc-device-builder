# TiRTC Porting Report

## Target

- Board ID: `{{BOARD_ID}}`
- Model/revision: `{{BOARD_MODEL_REVISION}}`
- Requested features: `{{REQUESTED_FEATURES}}`
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
- Firmware artifacts: `{{FIRMWARE_ARTIFACTS}}`
- Firmware SHA-256: `{{FIRMWARE_SHA256}}`
- Flash command/result: `{{FLASH_RESULT}}`

## Remaining work and risks

`{{REMAINING_WORK}}`

## Sanitization

Logs and artifacts were checked for device keys, Wi-Fi passwords, complete MQTT/WHIP tokens, and user media: `{{SANITIZATION_RESULT}}`.

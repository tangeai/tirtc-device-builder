# Generic TiRTC ESP32 developer intake prompt

Replace every `<...>` value. Write `unknown` when the fact is not known; do not remove the field or invite a guess.

```text
$tirtc-esp32-builder

Build a ThingConnect TiRTC port for this exact board revision. Start with evidence
and gates; generate and compile only after the requested features reach READY_TO_PORT.

Board identity
- Vendor: <vendor>
- Full sales model: <model>
- SoC/module: <full part number>
- PCB marking/hardware revision: <revision>
- Flash/PSRAM: <capacity and bus mode>
- I confirm the supplied schematic/BOM/BSP matches the physical board: <yes/no/unknown>
- Board photo directory: <absolute path or URL>

Requested product behavior
- H5 live video: <yes/no>
- H5 live audio: <yes/no>
- H5 talkback: <yes/no>
- AI bidirectional talk: <yes/no>
- Initial duplex policy: <half duplex/full duplex required>
- AEC requirement: <none/required with HIL>

Media contract
- H5-supported video codecs and contract version: <MJPEG/H264/H265 + document>
- Selected device video codec: <exactly one>
- Video stream ID and submission unit: <complete JPEG/Annex-B access unit/etc.>
- Refresh/key-frame behavior: <contract>
- Uplink audio codec/rate/bits/channels/stream: <values>
- H5 downlink audio codec/rate/bits/channels/stream: <values>
- AI audio codec/rate/bits/channels/stream: <values>

Board evidence
- Material root: <absolute path>
- Schematic/netlist: <absolute path>
- BOM: <absolute path>
- BSP: <path or repository URL plus commit/tag>
- Camera/record/playback examples: <paths or immutable links>
- Camera, codec, amplifier, IO-expander and module datasheets: <paths>
- Known-good logs/firmware and SHA-256: <paths or unknown>
- Known contradictions: <for example schematic sensor vs probed PID, or none>

Wi-Fi and onboarding
- Board/BSP-supported credential methods: <SoftAP/BLE/SmartConfig/factory NVS/custom/unknown>
- Preferred method for this port: <method or ask the assessor to select from evidence>
- Credential storage/injection: <NVS/encrypted NVS/secure factory tool/untracked dev config>
- Reprovision/reset mechanism: <method or unknown>
- ThingConnect binding methods: <verification code/factory bound/development credentials/custom>
- Selected binding method, stored-binding behavior, and reset API/doc: <values>
- Production credentials must remain outside source and reports: yes

Toolchain and platform
- ESP-IDF version: <version>
- Target: <for example esp32s3>
- TiRTC SDK platform/version: <values>
- Device Kit root or managed setup: <absolute path>
- Platform discovery endpoint/transport: <HTTP or HTTPS URL/environment>
- TiRTC SDK endpoint: <built in or explicit; keep separate from discovery>
- Transport staging: <for example HTTPS from start, or authorized HTTP L3-L5 baseline then HTTPS>
- Output project: <absolute path>

Required execution
1. Run Device Kit Doctor first and resolve every required failure.
2. Hash and inspect every supplied artifact. Generate Hardware IR v2; keep unknowns
   null and contradictions as issues.
3. Select only evidenced media and Wi-Fi profiles. Do not hardcode one board's sensor,
   codec, pins, or provisioning method into the Skill.
4. Before code, freeze camera identity/PID, I2C driver family, I2S/controller/GPIO/clock
   ownership, audio channel/TDM mapping, DMA/tasks, memory budget, onboarding states,
   and platform/TiRTC startup order.
5. Treat plaintext credentials committed to source as BLOCKED. SoftAP is optional when
   another evidenced, reprovisionable credential path exists.
6. Generate a board adapter; keep concrete board facts out of common H5/AI/TiRTC modules.
7. Add focused tests or post-link gates for each discovered invariant. Validate the final
   ELF, build, record BIN/ELF size and SHA-256, and output TIRTC_PORTING_REPORT.md.
8. Keep READY_TO_PORT, BUILD_VERIFIED, L2-L7, and HIL_VERIFIED separate. Bind runtime
   evidence to the exact firmware SHA-256. Change one high-risk variable per HIL run.
9. Do not access a serial port, flash, erase NVS, or monitor this turn. Flash only after I
   provide an exact port and explicit authorization for that artifact.
10. Never place Wi-Fi passwords, device keys, MQTT/WHIP/AI tokens, private keys, or user
    media in source, Hardware IR, logs, or reports.

Deliver doctor.json, hardware-ir.json, capability-assessment.json, dependency lock,
the buildable ESP-IDF project, policy tests, artifact hashes, TIRTC_PORTING_REPORT.md,
and every blocker with its smallest next action.
```

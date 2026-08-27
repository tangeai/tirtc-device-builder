# Reporting and acceptance

Use [the report template](../assets/report-template.md) and preserve separate `PASS`, `FAIL`, and `SKIP` results.

## Acceptance levels

| Level | Completion evidence |
|---|---|
| L-1 Environment | ESP-IDF version, target compiler, TiRTC SDK, build contract, and requested serial access pass doctor checks |
| L0 Generate | Project and Hardware IR exist; no existing output was overwritten |
| L1 Build | Hardware IR valid, SDK contract checked, `idf.py build` succeeds, artifacts recorded |
| L2 Boot | Exact chip/port resolved, flash succeeds, firmware boots without panic |
| L3 Online | Wi-Fi provisioning, binding, MQTT, and TiRTC reach ready state |
| L4 Media | Camera/microphone/speaker local paths work and counters/measurements are captured |
| L5 H5 | Browser receives the declared video/audio and talkback reaches the device |
| L6 AI | Token, WHIP, `start_session`, bidirectional audio, stop, and H5 recovery work |
| L7 Stability | Requested weak-network, repeated-session, resource, and soak criteria pass |

## Evidence

Record exact board revision, toolchain and SDK versions, source/adapter revisions, commands, return codes, firmware size and SHA-256, serial port/chip, sanitized log paths, browser or platform observations, and every unavailable dependency.

Reports describe observed current behavior. A `SKIP` caused by missing hardware, account, service, browser, or external network does not become a pass. If the user's requested completion level includes a skipped critical case, the final outcome remains incomplete.

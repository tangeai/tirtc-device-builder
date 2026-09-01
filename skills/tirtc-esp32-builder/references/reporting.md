# Reporting and acceptance

Use [the report template](../assets/report-template.md) and preserve separate `PASS`, `FAIL`, and `SKIP` results.

## Acceptance levels

| Level | Completion evidence |
|---|---|
| L-1 Environment | ESP-IDF version, target compiler, TiRTC SDK, build contract, and requested serial access pass doctor checks |
| L0 Generate | Project and Hardware IR exist; no existing output was overwritten |
| L1 Build | Hardware IR valid, SDK contract and requested-feature semantic gates pass, `idf.py build` succeeds, artifacts recorded |
| L2 Boot | Exact chip/port resolved, flash succeeds, firmware boots without panic |
| L3 Online | Wi-Fi provisioning, binding, MQTT, and TiRTC reach ready state |
| L4 Media | Camera/microphone/speaker local paths work and counters/measurements are captured |
| L5 H5 | Browser receives the declared video/audio and talkback reaches the device |
| L6 Sessions | AI, device-call and WeChat VoIP requested flows work; simultaneous capture/playback, AEC/double-talk, stop, timeout and H5 recovery are observed separately |
| L7 Stability | Requested weak-network, repeated-session, resource, and soak criteria pass |

Run and record the intake assessment before L0, the build assessment with `--project` and the exact artifact SHA-256 at L1, and the HIL assessment only when matching runtime evidence exists. Follow [firmware-delivery.md](firmware-delivery.md) for artifact location, retention, and mode-transition rules. Record actual byte size and SHA-256 in `build_evidence.artifacts[]`; the assessor reopens the file and rejects stale metadata. Missing serial or browser access is a `SKIP` for the affected L2-L7 levels, not an L0/L1 failure.

Keep `COMPILE_PASS` separate from `BUILD_VERIFIED`. When the compiler succeeds but a required runtime, audio, or video semantic gate fails or is missing, record the compiler result and report the feature and project as blocked. H5 image display is L5 evidence, never an inference from L1.

## Evidence

Record exact board revision, selected media, Wi-Fi, and binding profiles,
toolchain and SDK versions, source/adapter revisions, commands, return codes,
firmware version, application-BIN SHA-256, descriptor/full ELF SHA-256, serial
port/chip, sanitized log paths, browser or platform observations, and every
unavailable dependency. Never conflate the BIN and ELF hashes.

Runtime evidence belongs to one artifact. Label superseded artifacts and keep their observations as history; do not promote them to the current BIN/ELF. For HIL assessment, add the full SHA-256 to `runtime_evidence` and run `hardware_ir.py assess --phase hil --artifact-sha256 <sha> --strict`.

For L3-L7 media runs, capture the signals that distinguish software regressions from environment changes: onboarding/binding state, BSSID/channel/RSSI, reconnect or roaming events, audio/video send/receive/drop/error counters, queue watermarks, camera overflow count, internal heap/largest block, PSRAM, and measured latency when available. Never record credential values.

Reports describe observed current behavior. A `SKIP` caused by missing hardware, account, service, browser, or external network does not become a pass. If the user's requested completion level includes a skipped critical case, the final outcome remains incomplete.

# Workflow

## Select one branch

### Registered board

Use this branch when a board and exact hardware revision already have a Hardware IR plus a matching board media adapter.

1. Validate and assess the saved Hardware IR against the requested features.
2. Confirm that its BSP, ESP-IDF, TiRTC SDK, and adapter revisions are still resolvable.
3. Generate a new starter project without overwriting an existing path.
4. Install the matching board adapter and configuration overlay.
5. Build, optionally flash, execute the requested acceptance levels, and issue a fresh report.

The branch is complete when the new run has its own build and verification evidence; an older board report is provenance, not proof of the new artifact.

### New-board intake

Use this branch when the user supplies a board model, vendor URL, schematic, BOM, pin map, BSP, datasheets, photographs, or peripheral example projects without a verified adapter.

1. Resolve the full model, module, PCB marking, and hardware revision. Treat different revisions as different boards.
2. Prefer official schematic/BOM and BSP facts. For a PDF schematic, inspect page labels and net names; prefer an exported netlist, pin CSV, or vendor board definition when available.
3. Cross-check critical pins, clocks, power enables, reset lines, sensor/codec variants, and ESP-IDF version across at least two independent artifacts when possible.
4. Create the Hardware IR. Use `null` for unknown facts and retain contradictory values as an explicit issue instead of selecting one silently.
5. Validate and assess requested features. Ask only for unresolved facts that block the next safe step.
6. When all requirements reach `READY_TO_PORT`, generate the starter and implement the board adapter. When requirements remain blocked, generate only the IR, capability report, and an optional compile-safe skeleton if requested.

The branch is complete when every supplied artifact maps to an IR fact, provenance entry, contradiction, or declared irrelevant item.

### Existing project

Use this branch when the user supplies an ESP-IDF/BSP project instead of board documents.

1. Inspect its target, `sdkconfig`, partitions, component manifests/CMake, pin definitions, sensor and codec initialization, and working peripheral examples.
2. Build the existing minimal peripheral examples when the environment permits; code that compiles for a named target is stronger evidence than prose but does not prove hardware behavior.
3. Create the Hardware IR from the project and any companion hardware documents.
4. Preserve reusable vendor drivers behind the board adapter. Keep product UI and board code out of ThingConnect session/TiRTC modules.

The branch is complete when the reused and replaced parts are explicit and the original project remains intact unless the user requested in-place work.

## Repository document routing

Read only the documents for the active branch, but read each selected document completely.

- ESP32 starter or adapter work: `device-sim/device-sim-esp32/README.md`, `device-sim/ESP32_STARTER.md`, the selected SDK package README, and the generated template README.
- H5 live view or talkback: `device-h5-live.md`.
- AI intercom: `device-ai.md`.
- H5/AI switching, delayed callbacks, ownership, or timeouts: `device-session-model.md` and `device-session-arbiter.md`.
- Onboarding, binding, MQTT, token, or identity: `device-integration.md`.
- Public HTTP field or error changes: `api-reference.md` and `error-response-policy.md`.

## Generation and board seam

The runtime-facing `starter_media` interface stays stable. A reusable board integration should implement an internal `BoardMediaAdapterV1`-style adapter owned by `starter_media` rather than editing H5, AI, `starter_runtime`, or `starter_tirtc` for each board.

The adapter owns:

- camera capture and H.264 encoding tasks;
- microphone capture and audio encoding;
- downlink audio decode, buffering, codec, amplifier, and I2S playback;
- DMA buffers, hardware clocks, power, reset, GPIO, and key-frame requests;
- bounded stop, resource release, and generation-aware flushing.

The stable modules own stream IDs, negotiated/contracted formats, TiRTC callback copying, connection handles, session generation, and H5/AI sequencing.

## Verification loop

Use a bounded loop per layer: diagnose one failing invariant, make the smallest correction, and rerun that layer before moving forward. Stop and report when the remaining failure requires unavailable hardware, credentials, a new SDK binary, a public protocol change, or a user choice.

Do not use successful compilation as evidence for camera frames, speaker output, Web rendering, AI audio, or long-run stability.

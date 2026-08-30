# Workflow

## Select one branch

### Registered board

Use this branch only when `board_registry.py match` returns `exact` with
`safe_registered_reuse=true` and the package has a Hardware IR plus matching
board adapter.

1. Recheck every required runtime probe and reject a changed sensor/codec as a
   new variant.
2. Validate and assess the saved Hardware IR against the requested features.
3. Confirm that its BSP, ESP-IDF, TiRTC SDK, business protocol, and adapter
   revisions are still resolvable.
4. Generate a new starter project without overwriting an existing path.
5. Install the matching board adapter and configuration overlay.
6. Build, optionally flash, execute the requested acceptance levels, and issue a fresh report.

The branch is complete when the new run has its own build and verification evidence; an older board report is provenance, not proof of the new artifact.

### New-board intake

Use this branch when the user supplies a board model, vendor URL, schematic, BOM, pin map, BSP, datasheets, photographs, or peripheral example projects without a verified adapter.

1. Create `board-identity.json`, combine the developer's full model/PCB marking
   with safe SoC/component probes, and query the board registry. Treat different
   revisions or conflicting required probes as different variants. A probable
   or component match supplies hypotheses only.
2. Freeze the user-supplied product contract: selected video profile, audio/stream formats, duplex/AEC policy, supported Wi-Fi credential methods, selected onboarding method, transport staging, output path, and mutation boundary. Use `unknown` where the prompt lacks an answer.
3. Prefer official schematic/BOM and BSP facts. For a PDF schematic, inspect page labels and net names; prefer an exported netlist, pin CSV, or vendor board definition when available.
4. Cross-check critical pins, clocks, power enables, reset lines, sensor/codec variants, ESP-IDF version, resource ownership, and onboarding behavior across at least two independent artifacts when possible.
5. Create the Hardware IR v2. Use `null` for unknown facts and retain contradictory values as an explicit issue instead of selecting one silently. Store concrete board values in the IR/adapter rather than Skill files.
6. Validate and run the intake assessment. Classify unresolved facts by their next evidence source: source, implementation, build, HIL, or user input. Ask only for `user_blocked` facts that prevent a safe design. SoftAP is optional when another evidenced Wi-Fi credential method is available, keeps credentials outside source, and defines reprovisioning.
7. When hardware identity, wiring, product contracts, and an evidenced resource plan reach `READY_TO_PORT`, generate the starter and implement the board adapter. Generate a compile-safe adapter by default when remaining uncertainty is implementation-, build-, or HIL-resolvable. Stop at the IR/report only when missing user evidence or an incompatible dependency makes a safe implementation impossible.

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
- Device-to-device call: `device-call.md` and the applicable API reference.
- WeChat VoIP: `device-voip.md`, the mini-program integration document, and the
  applicable API reference.
- H5/AI switching, delayed callbacks, ownership, or timeouts: `device-session-model.md` and `device-session-arbiter.md`.
- Onboarding, binding, MQTT, token, or identity: `device-integration.md`.
- Public HTTP field or error changes: `api-reference.md` and `error-response-policy.md`.

## Generation and board seam

The runtime-facing `starter_media` interface stays stable. A reusable board integration should implement an internal `BoardMediaAdapterV1`-style adapter owned by `starter_media` rather than editing H5, AI, CALL, VOIP, `starter_runtime`, or `starter_tirtc` for each board.

The adapter owns:

- camera capture and the selected MJPEG/H.264/H.265 media path;
- microphone capture and audio encoding;
- downlink audio decode, buffering, codec, amplifier, and I2S playback;
- DMA buffers, hardware clocks, power, reset, GPIO, refresh/key-frame requests, and realtime task allocation;
- bounded stop, resource release, and generation-aware flushing.

The stable modules own the discovered TiRTC service endpoint, stream IDs,
negotiated/contracted formats, HTTP/MQTT business fields, TiRTC callback copying,
connection handles, pending calls, monotonic deadlines, session generation, and
H5/AI/CALL/VOIP sequencing. SDK lifecycle changes such as disconnect run in a
worker/state-machine context, never directly inside an SDK callback.

## Verification loop

Use a bounded loop per layer: diagnose one failing invariant, make the smallest correction, and rerun that layer before moving forward. Change one high-risk variable per HIL comparison. Turn reusable invariants into tests or post-link gates. Stop and report when the remaining failure requires unavailable hardware, credentials, a new SDK binary, a public protocol change, or a user choice.

For every generated H5/AI/call/VoIP project, validate `tirtc-runtime-contract.json` and run `install_runtime_gate.py <project>` before the ordinary build. Audio and video projects additionally install their media gates. AI/call/VoIP also require the full-duplex AEC result from the audio gate. A build that bypasses any applicable gate is not `BUILD_VERIFIED`.

When CALL or VOIP is requested, the runtime contract must also bind the project
to the pinned business protocol and unified session arbiter. First prove those
flows with the Linux C simulator. Simulator success establishes the protocol
baseline but cannot replace the ESP32 build or HIL levels.

Run the assessor once per layer:

- `--phase intake`: corroborated design evidence; success is `READY_TO_PORT`.
- `--phase build --project <project> --artifact-sha256 <sha>`: compile/semantic/post-link evidence; success is `BUILD_VERIFIED`.
- `--phase hil --artifact-sha256 <sha>`: matching L5/L6 runtime evidence; success is `HIL_VERIFIED`.

No serial authorization is required for L0/L1. When serial, browser, account, service, or network access is unavailable, complete the safe build work and report the affected L2-L7 levels as `SKIP`.

Do not use successful compilation as evidence for camera frames, speaker output, Web rendering, AI audio, or long-run stability. Bind every runtime conclusion to the tested firmware SHA-256.

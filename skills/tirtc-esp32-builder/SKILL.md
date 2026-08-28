---
name: tirtc-esp32-builder
description: Check or set up ESP-IDF, then generate, port, build, flash, and validate ThingConnect TiRTC ESP32 projects from a board model, schematic, BSP, pin map, or peripheral examples when H5 live view/talkback or AI intercom is requested. Use for environment diagnosis, supported-board generation, and new-board hardware intake; exclude Linux device-sim-c and server-only work.
---

# TiRTC Embedded Builder

Turn board evidence into an evidence-backed ESP-IDF project. Treat the Hardware IR as the single handoff between probabilistic document extraction and deterministic capability, generation, build, and verification steps.

## Start

1. Read [environment.md](references/environment.md). For a first-time setup or a request to check/install prerequisites, prefer `npx tirtc-device-builder@latest setup esp32`. Run its `--install` mode only when the user explicitly authorizes installation at the displayed destinations. The installer may create user-space files but never grants permission for `sudo` or persistent shell-profile edits.
2. Locate the versioned ESP32 Device Kit root containing `device-sim/` using the explicit input, `TIRTC_THING_CONNECT_ROOT`, the managed setup configuration, or workspace discovery. Treat its manifest and packaged protocol documents as the generation facts. If the user explicitly supplies a full ThingConnect source workspace, also read its applicable `AGENTS.md`.
3. Run the Doctor through the managed environment helper when one exists; otherwise run `python3 <skill-dir>/scripts/doctor.py --expected-idf 5.5 --target esp32s3`. Add `--require-workspace` when generation or repository reference documents are needed; a self-contained generated project can instead resolve its bundled SDK through `--project`. Resolve every required failure before claiming build readiness.
4. Read [workflow.md](references/workflow.md). Select the registered-board, new-board intake, or existing-project branch. The branch is selected when every supplied artifact has been accounted for and the exact board revision is known or explicitly unresolved.
5. Read [hardware-ir.md](references/hardware-ir.md) when a Hardware IR must be created or updated. New intake uses schema v2; schema v1 remains readable for existing H.264 projects. Record a source and verification level for every hardware fact that affects a requested feature.
6. Run `python3 <skill-dir>/scripts/hardware_ir.py validate <hardware-ir.json>` and then `assess --phase intake --strict`. `READY_TO_PORT` means the evidence is sufficient to design the adapter without guessing wiring or changing an unapproved public contract; it does not require a final ELF or runtime measurements.

Before stopping on `NEEDS_CONFIRMATION`, classify every unresolved fact as `source_resolvable`, `implementation_resolvable`, `build_resolvable`, `hil_resolvable`, or `user_blocked`. Resolve source facts by inspection. For implementation/build facts, record the evidenced design plan at `corroborated`, generate a compile-safe adapter, and verify it at L1. Defer HIL-only measurements to L2-L7 when hardware access is unavailable. Stop before implementation only for `user_blocked` facts such as unknown wiring or identity, a missing product choice, an unavailable SDK, or a required public-contract change.

## Build the project

Run `<device-kit-root>/device-sim/scripts/create_esp32_project.py` for the current ESP32-S3 H5/AI starter. Keep ThingConnect onboarding, H5, AI, TiRTC lifecycle, callback, stream, and generation behavior in the existing deep modules. Put board-specific camera, microphone, encoder, codec, amplifier, GPIO, DMA, and task behavior behind the `starter_media` seam or a board media adapter owned by it.

Before changing media code, read [capability-rules.md](references/capability-rules.md) and [porting-risks.md](references/porting-risks.md), then read the repository documents they route to. For requested audio, read [audio-contract.md](references/audio-contract.md); for requested video, read [video-contract.md](references/video-contract.md). Complete every applicable project-local semantic gate. A camera sensor alone does not establish H5 video support; validate the selected MJPEG, H.264, or H.265 profile end to end. Choose half duplex for AI when the supplied hardware and BSP do not establish a usable full-duplex/AEC path.

Keep the Skill board-agnostic. The prompt supplies product intent and artifact locations; Hardware IR stores evidence; the generated board adapter owns concrete sensors, codecs, pins, clocks, slots, DMA, and task allocation. Never add one board's values to Skill defaults to make an assessment pass.

Run focused tests before ESP-IDF build. Resolve the TiRTC SDK target and `manifest/build-contract.env` against the generated `sdkconfig`; a mismatched precompiled SDK is a blocked build, not a code-generation problem. Resolve managed components with `idf.py reconfigure`, then validate and install every applicable audio/video contract gate. A value copied from a “typical” header comment or a different sample rate is not clock evidence. A self-declared camera realtime or memory boolean is not video evidence.

After a successful build, promote only facts actually established by source, compile, semantic, or post-link gates to `build_verified`. Hash the exact BIN/ELF, record that exact hash under `build_evidence.artifacts[]`, and run `hardware_ir.py assess --phase build --project <project> --artifact-sha256 <sha256> --strict`. The assessment must reject a well-formed but unrecorded hash. A design plan at `corroborated` can pass intake but cannot pass the build phase. Report a successful compiler invocation as `COMPILE_PASS` when any requested feature gate is blocked; project-wide `BUILD_VERIFIED` requires every requested feature to pass.

## Flash and verify

Flash only when the user requested hardware mutation and the exact serial port and chip have been resolved. When more than one candidate device exists, obtain the target choice before writing. Keep credentials outside generated files and redact device keys, Wi-Fi passwords, MQTT/WHIP tokens, and user media from logs and reports.

Read [reporting.md](references/reporting.md) before end-to-end verification. Report every acceptance level as `PASS`, `FAIL`, or `SKIP`, with commands and evidence. Bind HIL observations to the exact firmware SHA-256 with `assess --phase hil --artifact-sha256`; an older artifact cannot verify a newer build. A build-only result is not H5 or AI completion; missing hardware, browser, account, service, or network evidence remains an explicit `SKIP` or blocker.

For HIL assessment, run `hardware_ir.py assess --phase hil --artifact-sha256 <sha256> --strict`. The HIL phase first requires build-verified paths, then promotes only features whose L5/L6 runtime evidence matches that exact artifact.

## Finish

Run `project_portability.py <project> --export` against the source-only deliverable; do not ship a machine-bound `build/` tree. Return the generated project path, Hardware IR, capability assessment, build artifacts, flash record when applicable, and `TIRTC_PORTING_REPORT.md`. The task is complete only when every requested feature is either verified at the requested level or named as a blocker with the smallest next action that can resolve it.

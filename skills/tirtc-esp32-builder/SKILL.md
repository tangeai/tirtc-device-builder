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
5. Read [hardware-ir.md](references/hardware-ir.md) when a Hardware IR must be created or updated. Record a source and verification level for every hardware fact that affects a requested feature.
6. Run `python3 <skill-dir>/scripts/hardware_ir.py validate <hardware-ir.json>` and then `assess --strict`. Generation may proceed for a requested feature only when it is `READY_TO_PORT` or `HIL_VERIFIED`; otherwise report the exact missing evidence and continue with safe discovery or scaffolding only.

## Build the project

Run `<device-kit-root>/device-sim/scripts/create_esp32_project.py` for the current ESP32-S3 H5/AI starter. Keep ThingConnect onboarding, H5, AI, TiRTC lifecycle, callback, stream, and generation behavior in the existing deep modules. Put board-specific camera, microphone, encoder, codec, amplifier, GPIO, DMA, and task behavior behind the `starter_media` seam or a board media adapter owned by it.

Before changing media code, read [capability-rules.md](references/capability-rules.md) and the repository documents it routes to. A camera sensor alone does not establish H5 video support; the complete H.264 Annex-B and key-frame path must be evidenced. Choose half duplex for AI when the supplied hardware and BSP do not establish a usable full-duplex/AEC path.

Run focused tests before ESP-IDF build. Resolve the TiRTC SDK target and `manifest/build-contract.env` against the generated `sdkconfig`; a mismatched precompiled SDK is a blocked build, not a code-generation problem.

## Flash and verify

Flash only when the user requested hardware mutation and the exact serial port and chip have been resolved. When more than one candidate device exists, obtain the target choice before writing. Keep credentials outside generated files and redact device keys, Wi-Fi passwords, MQTT/WHIP tokens, and user media from logs and reports.

Read [reporting.md](references/reporting.md) before end-to-end verification. Report every acceptance level as `PASS`, `FAIL`, or `SKIP`, with commands and evidence. A build-only result is not H5 or AI completion; missing hardware, browser, account, service, or network evidence remains an explicit `SKIP` or blocker.

## Finish

Return the generated project path, Hardware IR, capability assessment, build artifacts, flash record when applicable, and `TIRTC_PORTING_REPORT.md`. The task is complete only when every requested feature is either verified at the requested level or named as a blocker with the smallest next action that can resolve it.

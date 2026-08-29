# Changelog

This project follows Semantic Versioning.

## 0.7.0

- Separate the platform/Web video contract (MJPEG, H.264, and H.265 on stream 11) from the single codec profile selected by a board; keep the LCKFB ESP32-S3 adapter on MJPEG without narrowing platform capability.
- Add a mandatory runtime semantic gate for service-endpoint wiring, callback-safe lifecycle changes, exact downlink media filtering, authoritative AI session-format validation, and remote session termination.
- Reject invented, concatenated, absolute, missing, or hash-mismatched Hardware IR source locators and verify recorded build artifacts against the actual project-relative files.
- Treat the entire ESP-IDF `build/` tree as non-portable, retain verified deliverable copies under `artifacts/`, and strengthen Doctor handling and negative regression tests.
- Package the hardened generated starter and platform/runtime contracts in ESP32 Device Kit 1.1.1.

## 0.6.0

- Add project-local audio and video semantic contracts that verify codec clock tables, I2S/TDM topology, selected video framing, dependency locks, scheduler isolation, sensor policy, and memory/backpressure before an artifact can reach `BUILD_VERIFIED`.
- Require build assessment hashes to match `build_evidence.artifacts[]`, and propagate requested-feature failures to the project gate without downgrading an existing `BLOCKED` result.
- Add portable CMake gate installers, source-export checks, a clean-room LCKFB ESP32-S3 prompt, and regression coverage for MJPEG, H.264, and H.265 video contracts.
- Distinguish compiler success from capability verification and document source-only transfer to another machine.

## 0.5.0

- Split Hardware IR assessment into explicit `intake`, `build`, and `hil` phases so implementation- and build-resolvable facts do not require runtime proof before adapter work begins.
- Add `BUILD_VERIFIED` with exact artifact SHA-256 binding, while keeping L5/L6 runtime evidence exclusive to `HIL_VERIFIED`.
- Classify unresolved facts by their next evidence source and stop pre-build work only for facts that genuinely require user input, unavailable hardware/SDK, or a public-contract decision.
- Update the developer intake prompt and reporting guidance so missing serial access produces L2-L7 `SKIP` results without blocking L0/L1.
- Add phase regression coverage while retaining schema v1 compatibility and independent MJPEG, H.264, and H.265 profile validation.

## 0.4.0

- Add Hardware IR v2 with selected MJPEG, H.264, or H.265 video profiles while retaining schema v1 compatibility.
- Gate I2C driver-family consistency, I2S/GPIO ownership, audio channel mapping, camera realtime policy, and startup/media memory budgeting.
- Model Wi-Fi credential methods independently from board hardware: SoftAP, BLE, SmartConfig, factory NVS, development configuration, or documented custom provisioning can be selected from evidence.
- Block credentials committed to source and require a reprovisioning path plus a selected verification-code/factory/custom binding profile, stored-binding handling, and reset behavior.
- Bind HIL status to the exact firmware SHA-256 and acceptance level instead of inheriting evidence from older artifacts.
- Add a board-agnostic developer intake prompt and bring-up risk gates covering sensor identity, TLS/memory, Wi-Fi quality, media counters, and one-variable HIL diagnosis.

## 0.3.0

- Add reproducible packaging for a minimal, checksummed ESP32-S3 Device Kit release asset.
- Download, verify, cache, and reuse the pinned Device Kit instead of cloning the full ThingConnect source repository during automatic setup.
- Add a read-only `setup esp32` check that reports the smallest next action.
- Add `setup esp32 --install` for resumable user-space installation of the Codex Skill, versioned ESP32 Device Kit, ESP-IDF 5.5.4, and ESP32-S3 tools.
- Reuse valid existing workspaces and ESP-IDF installations without overwriting them.
- Keep system package installation and persistent shell-profile changes outside automatic setup.
- Save a path-only managed configuration and environment helper for later Skill runs.

## 0.2.0

- Publish the repository as the `tirtc-device-builder` npm package.
- Add an explicit `npx tirtc-device-builder install esp32` flow without lifecycle installation scripts.
- Preserve existing Skill installations unless the caller supplies `--force`.
- Run the packaged ESP32 environment doctor through the npm CLI.
- Validate npm/plugin version alignment and the public tarball in CI.
- Support npm trusted publishing from version tags after the initial manual release.

## 0.1.0

- Package the ESP32 workflow as `tirtc-esp32-builder`.
- Diagnose ESP-IDF 5.5.x, target tools, ThingConnect workspace, TiRTC SDK contract, project configuration, and serial access.
- Validate Hardware IR evidence and assess H5 live-view, talkback, and AI-intercom readiness.
- Provide a skills-only Plugin manifest, public installation guide, package validation, and CI.

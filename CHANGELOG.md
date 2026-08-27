# Changelog

This project follows Semantic Versioning.

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

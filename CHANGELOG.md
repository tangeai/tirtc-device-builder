# Changelog

This project follows Semantic Versioning.

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

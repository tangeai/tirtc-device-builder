# ESP-IDF environment

Run the doctor before generation, build, flash, or monitor:

```bash
python3 <skill-dir>/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --require-workspace
```

Add `--project <generated-project>` after generation so the doctor can compare `sdkconfig` or `sdkconfig.defaults` with the TiRTC SDK build contract. Use `--json` when the result will be included in another report.

## ThingConnect workspace

This distributable skill does not bundle the ThingConnect source tree or TiRTC static library. Resolve the public ThingConnect workspace in this order:

1. an explicit `--thing-connect-root <path>`;
2. `TIRTC_THING_CONNECT_ROOT`;
3. an ancestor of the project or current directory containing `device-sim/scripts/create_esp32_project.py`;
4. an ancestor whose `thing-connect/` child contains that generator.

The public source is `https://github.com/tangeai/tirtc-server-example`. Clone it only into an explicit destination. The root accepted by the doctor may be either the repository root or its `thing-connect/` child.

SDK resolution is independent after generation: an explicit `--sdk-dir` wins, followed by `<project>/third_party/tirtc`, then the SDK packaged in the resolved ThingConnect workspace. The generated project path therefore remains diagnosable after it is moved away from the source repository.

## Required checks

- `python3`, `git`, `idf.py`, and the target compiler are available in the active shell;
- `idf.py --version` matches the project's required ESP-IDF line;
- `IDF_PATH` is coherent when set;
- the TiRTC SDK contains its header, archive, and `manifest/build-contract.env`;
- generated Kconfig values explicitly match TiRTC's FreeRTOS ABI-sensitive contract;
- the requested serial port exists and is writable before flash or monitor.

CMake and Ninja are reported separately because an activated ESP-IDF environment may provide or select its own managed versions.

## Missing ESP-IDF

Checking is read-only. Installing ESP-IDF downloads code and tools, consumes disk space, and may change the developer's shell setup, so perform it only after the user approves the exact version, install directory, supported target, and shell activation method.

For an approved installation:

1. Confirm the project and TiRTC package require the same ESP-IDF major/minor line. This repository's current ESP32-S3 starter requires 5.5.x.
2. Consult the current official Espressif installation instructions for the developer's operating system.
3. Install a pinned 5.5.x release into a user-approved directory; enable the `esp32s3` target and keep the vendor installer logs.
4. Activate the installed environment in the current shell. Modify a persistent shell profile only when the user explicitly requests it.
5. Rerun the doctor. Installation is complete only when the IDF version, compiler, SDK files, and project contract checks pass.

When downloads, package installation, administrator rights, USB drivers, or group membership are required, surface the exact action and obtain the applicable authorization instead of treating it as an ordinary code edit.

## Existing but inactive ESP-IDF

If `IDF_PATH/tools/idf.py` exists but `idf.py` or the target compiler is absent from `PATH`, report the environment as inactive. Activate that installation using its vendor-provided export script and rerun the doctor; do not install a second copy merely because the current shell is inactive.

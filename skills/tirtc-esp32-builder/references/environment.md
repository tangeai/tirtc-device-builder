# ESP-IDF environment

## Managed one-command setup

Prefer the packaged setup entrypoint for a new machine:

```bash
npx tirtc-device-builder@latest setup esp32
npx tirtc-device-builder@latest setup esp32 --install
```

The first command is read-only. The second command is explicit authorization to install missing user-space components at the printed destinations. Its default root is `~/.tirtc-device-builder`; it downloads and verifies the pinned ESP32 Device Kit, installs the Skill, clones or reuses ESP-IDF 5.5.4, runs Espressif's `install.sh esp32s3`, writes `config.json` and `env.sh`, and reruns the Doctor inside the activated environment.

The automatic branch never runs `sudo` or modifies a persistent shell profile. When system dependencies are missing, report its exact blocker and let the user perform the displayed system action. Existing incomplete directories are preserved as blockers. Rerunning the same command resumes completed stages.

When `<setup-root>/env.sh` exists, use it only as an activation prefix for the current command:

```bash
bash -lc '. "<setup-root>/env.sh" && python3 "<skill-dir>/scripts/doctor.py" --expected-idf 5.5 --expected-kit 1.1.1 --target esp32s3 --require-workspace'
```

The helper contains paths, not device or network credentials. Read `<setup-root>/config.json` when exact managed paths are needed; the environment helper does not authorize unrelated downloads, shell-profile changes, flashing, or credential writes.

Run the doctor before generation, build, flash, or monitor:

```bash
python3 <skill-dir>/scripts/doctor.py \
  --expected-idf 5.5 \
  --expected-kit 1.1.1 \
  --target esp32s3 \
  --require-workspace
```

Add `--project <generated-project>` after generation so the doctor can compare `sdkconfig` or `sdkconfig.defaults` with the TiRTC SDK build contract. Use `--json` when the result will be included in another report.

## ESP32 Device Kit

The automatic setup downloads a versioned minimal Kit instead of cloning the ThingConnect server repository. A managed Kit is ready only when its generator and SDK files exist and `manifest.json` declares the exact pinned `kit_version`. A stale environment or managed configuration that points at an older Kit is ignored in favor of the current versioned managed path. The setup configuration records the version read from that manifest; it never substitutes the desired version for the actual one.

The installed Skill has its own `<skill-dir>/VERSION` marker. Setup requires it to equal the npm package version and reports both values. Replacing a missing or mismatched marker requires the explicit `--install --force-skill` flow and a new Codex session.

For an explicitly selected legacy workspace, omit `--expected-kit`; otherwise resolve the generation root in this order:

1. an explicit `--thing-connect-root <path>`;
2. `TIRTC_THING_CONNECT_ROOT`;
3. an ancestor of the project or current directory containing `device-sim/scripts/create_esp32_project.py`;
4. an ancestor whose `thing-connect/` child contains that generator.

The default managed root is `<setup-root>/kits/esp32s3/<kit-version>`. The public ThingConnect workspace remains an optional legacy/development input; the doctor accepts either a Device Kit root, a repository root, or its `thing-connect/` child.

SDK resolution is independent after generation: an explicit `--sdk-dir` wins, followed by `<project>/third_party/tirtc`, then the SDK packaged in the resolved Device Kit or legacy workspace. The generated project remains diagnosable after it is moved away from the Kit.

Before copying a generated project to another machine, run:

```bash
python3 <skill-dir>/scripts/project_portability.py <generated-project> --export
```

Copy source inputs only. Never export `build/`: CMake caches absolute source, toolchain, and Python paths from the originating machine. `managed_components/` may be regenerated from the committed `dependencies.lock`; the bundled `third_party/tirtc` SDK and its build contract must remain in the source package. CMake must invoke shell gates through `bash <script>` so the build does not depend on archive- or filesystem-specific executable bits.

The export check also requires Hardware IR, every requested-feature semantic
contract, `sdkconfig.defaults`, a referenced custom partition table, and each
artifact retained in `build_evidence.artifacts[]`. Inside a Git worktree these
inputs must not be untracked files hidden by `.gitignore`. Ignore local build
trees and intermediate firmware snapshots, then explicitly include the exact
validated release bundle used by retained evidence.

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

# Firmware identity and delivery

Read this reference whenever the task builds, flashes, hands off, compares, or
retains firmware. Select the delivery mode from the user's immediate goal; do
not force a release bundle onto a quick device-test loop.

## Choose one mode explicitly

### Development flash

Use this mode for rapid build/flash/monitor iteration on one development
machine. Keep the normal ESP-IDF `build/` tree and use the ordinary command:

```bash
idf.py -p <exact-port> flash monitor
```

Do not create a new archive or make the user manually flash bootloader,
partition-table and application BIN files when `idf.py flash` can resolve the
build metadata. Before flashing, record the application version and hash of the
exact application BIN. A build assessment may bind to a project-relative file
under `build/`; that evidence remains valid only while that exact file exists.

If an experiment produces runtime evidence worth retaining, copy the unchanged
BIN and matching ELF into `artifacts/` before the next rebuild, record their
sizes and hashes, and update the report. Copying does not create a new firmware
identity; a rebuild does.

### Evidence bundle

Use this mode for a portable handoff, release candidate, rollback image,
retained HIL result, or source export. Keep project-relative copies of the exact
application BIN and ELF, plus bootloader and partition-table files when the
recipient needs manual flashing. Record byte sizes and SHA-256 values in
Hardware IR, run strict build assessment, then run
`project_portability.py --export` on the source-only delivery tree.

When promoting a development build into an evidence bundle, copy the unchanged
files first, then replace every retained `build/...` artifact path in Hardware
IR and the report with its new `artifacts/...` path. Remove transient build
records that are not being retained; do not merely add bundle records beside
stale paths. Rerun strict build assessment against the copied application-BIN
hash so the assessor reopens the new path. The source-only export is ready only
when every `build_evidence.artifacts[]` path exists outside `build/` and the
matching report identifies the same hashes.

Only this export workflow requires removal of the machine-bound `build/` tree.
Do not delete it during active iteration, and never delete a user-owned build
tree merely to make a report look portable.

## Make firmware self-identifying

Set an explicit, human-readable `PROJECT_VER` before `project()` in the top-level
ESP-IDF `CMakeLists.txt`. Keep it at 31 UTF-8 bytes or fewer so it fits the
`esp_app_desc_t.version` field with its terminator. Use a label that states what
the image is: for example `audio-repro.2`, `button-test.1`, `fix.3`, or a release
version. A build that deliberately preserves a known bug is a reproduction or
diagnostic image, not a fix.

At boot, log `project_name`, `version`, build date/time, IDF version, and the
full ELF SHA-256 from `esp_app_get_description()` or
`esp_app_get_elf_sha256()`. If the product has a console, expose the same fields
through `version` or `status`. This lets a tester distinguish a successful
flash of the wrong image from a runtime regression.

Verify the built application BIN before flash or handoff:

```bash
python3 <skill-dir>/scripts/firmware_identity.py build/<app>.bin \
  --elf build/<app>.elf --expect-version <expected-version>
```

The script reads the embedded ESP-IDF application descriptor, verifies the
explicit version, and confirms that the supplied ELF's full SHA-256 matches the
descriptor. It accepts an application BIN, not a merged whole-flash image.

## Name hashes precisely

The outer application-BIN SHA-256 and the descriptor's full ELF SHA-256 identify
different files. Record both with unambiguous labels; do not call either one
simply “firmware hash.” Bind Hardware IR artifacts and HIL observations to the
exact retained artifact SHA required by the assessor, and include the boot-log
version/full ELF hash so the physical device can be reconciled with that record.

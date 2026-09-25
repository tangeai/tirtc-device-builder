# Hardware diagnostics

Use this reference when identifying a board or designing/running its probe.

## Evidence model

For every fact record a `state`, `method`, and `source`:

| State | Meaning |
|---|---|
| `unknown` | No safe observation exists yet. |
| `declared` | A schematic, BSP configuration, device table, or compiled driver says it should exist. |
| `detected` | A runtime identity/read/init transaction succeeded on the exact board. |
| `measured` | Software obtained a quantitative value such as bytes, sample level, or coordinates. |
| `verified` | An active test and its observation passed on the exact board and firmware. |
| `unsupported` | An authoritative source or safe test establishes absence/incompatibility. |

Evidence is monotonic only for the same board revision and firmware artifact.
When sources disagree, retain both under `issues`; do not silently promote the
preferred value.

## What can and cannot be discovered

### Display and touch

Read the initialized LCD driver's width, height, bus and pixel format, then draw
a versioned pattern containing corner markers, color bars and text. Driver
registration is only `declared`; successful init/read-ID is `detected`; a human
or camera observation of the complete pattern is `verified`.

Touch probing requires a known BSP bus/pin profile. Read the controller ID when
supported, then collect raw and mapped coordinates at corners and center.
Report display and touch rotation separately. An I2C ACK alone does not prove a
touch panel, and broad address scans can disturb unrelated devices.

The panel's physical diagonal is generally not electronically discoverable.
Report pixel dimensions from the driver and physical millimetres only from an
exact panel/board source or a calibrated measurement.

### Audio

Separate `microphone`, `speaker`, `codec`, `capture`, `playback`, `duplex`,
`reference`, and `aec`. A codec responding on a control bus does not prove that
a microphone, amplifier, or loudspeaker is fitted.

For capture, record the actual PCM sample rate, sample bits, valid bits,
channels, channel/slot mapping and frame size. Run a bounded capture and report
sample count, min/max, DC mean, RMS, clipping count and zero/stuck ratio. Ambient
energy is evidence of a live path, not proof of speech quality.

For playback, require an explicit test action, ramp the level, emit a bounded
tone/chirp, and record whether output was observed. Duplex/AEC tests additionally
require simultaneous RX/TX, a real playback-reference path, far-end-only,
near-end-only and double-talk observations.

### Flash and memory

Read SoC/revision and Flash JEDEC/SFDP or the SDK's physical-capacity API. Also
report application-usable partition bytes; physical Flash and usable firmware
space are different facts. Never infer capacity only from the linker layout.
On Beken v3.1.1, `bk_flash_get_current_total_size()` is the selected driver's
mapped size and may come from a fallback table entry when JEDEC ID is unknown.
Report it as `mapped_bytes`; keep `physical_bytes` unknown until the ID is
recognized, and report `recognized` explicitly.

Report internal SRAM total when the SDK exposes it, free bytes after boot,
minimum-ever-free bytes and largest allocatable block. Report PSRAM separately
and include capability flags for DMA/internal-only allocations. Re-measure after
LCD/audio/TiRTC initialization and during the worst requested session.

## Safe probe order

1. Read-only chip, reset reason, SDK, Flash and heap observations.
2. Introspect the selected board profile and initialized driver registry.
3. Read identities only on known buses, pins and addresses from the exact BSP.
4. Run display and touch tests.
5. Run microphone capture, then user-triggered speaker playback.
6. Run duplex/reference/AEC tests only after volume and routing are controlled.
7. Repeat memory measurements inside the final XiaoTai firmware.

The order is complete when every requested product capability maps to concrete
evidence or a named unresolved test.

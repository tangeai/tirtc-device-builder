---
name: tirtc-esp32-builder
description: Identify, generate, port, build, flash, validate, and capture reusable knowledge for TiRTC ESP32-S3 or ESP32-P4 boards from a model, schematic, BSP, pin map, peripheral examples, or an existing ESP-IDF project. Use for H5 live view/talkback, AI intercom, device-to-device calls, WeChat VoIP, board detection, memory/AEC bring-up, or reusable board registration; exclude server-only work and unrelated embedded projects.
---

# TiRTC ESP32 Builder

Turn board evidence into a verified ESP-IDF product port. Hardware IR is the
handoff from probabilistic document extraction to deterministic generation and
gates. The curated board registry preserves reusable results without treating a
past build as proof for a new artifact.

## 1. Establish the platform and inputs

1. Read this Skill's `VERSION`, then read [environment.md](references/environment.md),
   [workflow.md](references/workflow.md), and
   [TiRTC platform contract](references/tirtc-platform.md). Record the installed
   Skill version rather than inferring it from a prompt or npm output.
2. Freeze the requested product features independently: H5 live audio/video and
   talkback, AI intercom, device-to-device calling, and WeChat VoIP. Do not
   silently remove a requested feature because the current starter lacks it.
3. Resolve a versioned source of truth. The managed ESP32-S3 Device Kit is the
   default for its packaged capabilities. Device-call/WeChat simulation or
   protocol porting requires a pinned full `tirtc-server-example` checkout when
   those sources are absent from the selected Kit. Clone or download it only
   when the user authorizes that external write. Read applicable repository
   instructions and the exact business documents routed by `workflow.md`.
4. Run Doctor for the exact target and SDK package. Managed generation currently
   automates ESP32-S3. ESP32-P4 is valid only with an evidenced P4 BSP/network
   path and the matching `espressif_esp32p4` SDK/build contract; never link the
   S3 archive into a P4 image.

## 2. Identify the board and query knowledge

Read [board-knowledge.md](references/board-knowledge.md). Combine developer-
declared vendor/model/PCB revision with safe observations such as SoC, module,
Flash/PSRAM, camera PID and codec IDs. The SoC cannot determine carrier-board
wiring or PCB revision by itself.

Run `board_registry.py match` before selecting a workflow branch. Only an exact
identity with `safe_registered_reuse=true` selects the registered-board branch.
A probable match supplies hypotheses; a component match supplies only component
lessons. Any identity conflict creates a new variant and keeps concrete GPIO,
clock, DMA and task values unresolved.

## 3. Prove the business flows before board porting

When device-call or WeChat VoIP is requested, first build and run the pinned
Linux C simulator with file-backed media. Verify the requested H5, AI, `call
<device_id> [video|audio]`, and `wxcall [N] [video|audio]` paths plus accept,
reject, cancel, hangup, timeout and recovery behavior. This establishes the
business protocol and state model; it does not verify ESP32 hardware.

Preserve one process-wide TiRTC lifecycle and one unified Router → Arbiter →
Coordinator path. STREAM is the H5 baseline; VOIP, AI and CALL are foreground
owners unless the product contract explicitly proves parallel resources.
Callbacks enqueue bounded events. A single state-owning task handles HTTP,
MQTT, connection lifecycle, generation checks and monotonic deadlines.

## 4. Create and assess Hardware IR

For a new or changed board, read [hardware-ir.md](references/hardware-ir.md),
create schema v2, validate it, and run strict intake assessment. Record a source
and verification level for every identity, pin, clock, slot, media, memory,
onboarding and business fact. Keep contradictions and unknowns explicit.

Classify unresolved facts as `source_resolvable`, `implementation_resolvable`,
`build_resolvable`, `hil_resolvable`, or `user_blocked`. Resolve all safe source,
implementation and build facts. Stop before code only for a genuine user choice,
unknown wiring/identity, unavailable matching SDK, or required public-contract
change.

## 5. Generate and port

Generate a new project without overwriting an existing path. Keep platform
onboarding, MQTT, TiRTC lifecycle, session routing/arbitration and stream
contracts in stable modules. Put camera, microphone, encoder, codec, amplifier,
GPIO, DMA, AEC and realtime task behavior behind `starter_media` or its board
adapter.

Treat AEC as mandatory for `ai_talk`, `device_call`, and `wechat_voip`. Do not
certify those features through a half-duplex fallback. Hardware IR must prove
simultaneous capture/playback, a physical playback-reference path, and an
available AEC implementation. The build gate must additionally prove
`shared_clock.directions_simultaneous=true` and
`echo_cancellation.enabled=true`; otherwise the affected feature is `BLOCKED`.
H5 talkback alone may remain half-duplex only when the requested product
contract explicitly permits it.

Follow the lifecycle from the locked C header: configure pre-init-only options
such as `TIRTC_OPT_MAX_SEND_BUFFER`, call `TiRtcInit()`, set the device secret and
client ID from an untracked runtime source, call `TiRtcStart()`, and wait for
`TIRTC_EVENT_SYS_STARTED`. `TiRtcStart()` returning zero is not readiness.

Before media work, read [capability-rules.md](references/capability-rules.md) and
[porting-risks.md](references/porting-risks.md). For requested audio, video or
H5/AI/call runtime behavior, read and install the applicable semantic contracts.
Keep concrete board values in Hardware IR, contracts and adapter files rather
than Skill defaults.

When the product request includes a physical button, touch input, reset, power
key, wake source or enclosure label, read
[product-controls.md](references/product-controls.md). Treat the exact physical
product as baseboard plus any carrier, PMIC and enclosure controls. Board input
code emits bounded intents to the state-owning runtime; it does not own session
lifecycle.

## 6. Build and assess

Read [firmware-delivery.md](references/firmware-delivery.md) and select
`development flash` or `evidence bundle` from the user's current goal. Run
focused tests, resolve managed components, validate the exact SDK
`manifest/build-contract.env`, install every applicable semantic gate, then run
the ordinary ESP-IDF build. Requested call/VoIP features must be represented by
the runtime/business contract and the unified arbiter implementation; an H5/AI-
only starter cannot reach `BUILD_VERIFIED` for those features.

Set an explicit firmware version, verify the application descriptor and full
ELF identity with `firmware_identity.py`, and record the application-BIN hash
with its exact label. Follow the selected delivery mode's artifact paths and
retention rules, record actual size and SHA-256 in Hardware IR, then run strict
build assessment with `--project` and that exact hash. Compiler success with a
missing feature gate is `COMPILE_PASS`, not product completion.

## 7. Flash, verify, and learn

Flash only with explicit authorization and an exact serial target. Read
[reporting.md](references/reporting.md). Record every level as PASS, FAIL or SKIP
and bind HIL observations to the exact artifact SHA-256. Verify local media,
H5, AI, device-call, WeChat VoIP, AEC/double-talk when requested, recovery,
weak-network behavior and stability separately.

For every AEC-required flow, run speaker-active near-end speech, far-end-only,
double-talk, rapid session switching and reconnect cases. Watchdog survival or
clean audio in one mode cannot substitute for these per-mode observations.

After assessment, generate a project-local board-knowledge candidate. Promotion
is a reviewed repository change: classify lessons as generic, component or exact
board; attach artifact evidence; add regression tests for generic invariants;
then publish a new Skill/registry version. Never let an installed Skill mutate
itself from conversation history.

Complete the selected mode's retention or export checks from
`firmware-delivery.md`. Return the project, Hardware IR, identity match,
capability result, exact artifacts, flash command when applicable, and report.

## Security boundary

Keep AccessKey, SecretKey, device keys, Wi-Fi passwords, MQTT/WHIP tokens,
certificates, MAC-derived identifiers and user media outside source, prompts,
registries and reports. Inject secrets through an untracked configuration,
provisioning store, secure NVS or a product keystore. Redact logs. Installation,
cloning, flashing, erasing NVS, browser/account use and registry promotion each
retain their own authorization boundary.

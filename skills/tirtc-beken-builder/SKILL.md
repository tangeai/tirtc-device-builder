---
name: tirtc-beken-builder
description: Diagnose, port, build, flash, and validate XiaoTai/TiRTC firmware for BK7258, BK7259, and closely related Beken boards using an official Beken SDK project, board evidence, and on-device probes. Use for display/touch, microphone/speaker, Flash/RAM, media/AEC capability, or XiaoTai H5/AI/call integration; exclude ESP32 projects and unsupported guesswork from a SoC name alone.
---

# TiRTC Beken Builder

Turn a physical BK board into an evidence-backed XiaoTai port. A probe report is
the boundary between documentation hypotheses and what the exact firmware saw on
the exact board. Never infer carrier-board wiring, fitted peripherals, or PCB
revision from `BK7258`/`BK7259` alone.

Read [architecture](references/architecture.md) when planning a new product or
explaining the platform split and delivery stages.
Read [BK probe research](references/bk-research.md) when selecting an SDK line,
implementing a probe, or checking the primary-source basis for an API.
Read [LCKFB BK7258 lessons](references/lckfb-bk7258-lessons.md) before porting
XiaoTai/TiRTC to BK7258, reviewing a BK7258 product project, or accepting its
build. Apply the gates to the target's evidence; copy the case-study constants
only when its board, SDK and binary identities match.

## 1. Establish the target

1. Read this Skill's `VERSION`, then read
   [hardware diagnostics](references/hardware-diagnostics.md) and
   [TiRTC integration](references/tirtc-integration.md).
2. Record the exact board model/PCB marking, SoC, official SDK or BSP repository
   and revision, toolchain, bootloader/partition layout, and the requested
   XiaoTai features. Keep unavailable facts `null`.
3. Prefer the board vendor's working SDK project. Treat a similar board's pin
   map only as a hypothesis. Preserve its bootloader, partition table, RF
   calibration, secure-boot data, and factory data unless the user explicitly
   authorizes changing them.
4. Inspect the selected SDK headers and examples before naming APIs. Beken SDK
   branches differ; source-visible symbols in the pinned checkout outrank prose
   and this Skill. Start discovery from <https://docs.bekencorp.com/>,
   <https://github.com/bekencorp/> and the official Gitee mirror. For the
   reproducible BK7258 Kit baseline, use official Gitee tag
   `release/v3.1.1.8` at commit
   `1cfd56af09a3cb6470f35f1e0c604035ed1b6ee7`. A locally delivered
   `3.1.1.8-20260605` tree is modified reference material, not that baseline.

Run the read-only environment check when a checkout is available:

```bash
python3 <skill-dir>/scripts/doctor.py --sdk-root <bk_avdk_smp>
```

## 2. Build the diagnostic firmware

Follow [probe porting](references/probe-porting.md). Add a small diagnostic task
to the known-working board project and implement the adapter against that pinned
SDK. It emits one framed JSON object beginning with `TIRTC_BK_PROBE `.

Probe in three layers:

- **Intrinsic:** chip/revision, Flash JEDEC ID and usable partition bytes, SRAM
  and optional PSRAM totals/free/largest block.
- **Enumerated:** compiled board profile, initialized LCD/touch/audio drivers,
  controller or codec identities, buses, dimensions and advertised formats.
- **Active:** LCD pattern, touch coordinates, microphone capture statistics,
  speaker test tone, simultaneous capture/playback, playback reference and AEC.

Use targeted, BSP-approved buses and addresses. Generic GPIO toggling, blind
bus scans, destructive Flash writes, and audio output without an explicit test
action are outside discovery. A linked driver is `declared`; only a successful
runtime transaction is `detected`, and only an active observation is `verified`.

Collect and assess the report:

```bash
python3 <skill-dir>/scripts/bk_probe_report.py init probe-report.json
python3 <skill-dir>/scripts/bk_probe_report.py collect serial.log probe-report.json
python3 <skill-dir>/scripts/bk_probe_report.py validate probe-report.json
python3 <skill-dir>/scripts/bk_probe_report.py assess probe-report.json
```

The probe run is complete when every required field is a measured value,
explicitly unsupported, or an `unknown` with a named next action. Compilation is
not evidence that a peripheral exists.

## 3. Decide the product shape

Read [capability rules](references/capability-rules.md). Run assessment before
porting business code. Preserve separate conclusions for display-only UI,
touch UI, button/voice control, H5 uplink, H5 talkback, AI conversation, device
call, and WeChat VoIP.

Do not manufacture a click UI for a display without verified touch. Prefer a
status/voice UI; use buttons only when the enclosure exposes enough verified
controls and the product interaction has an unambiguous mapping. Missing screen
or touch does not by itself block audio-only XiaoTai.

AI and call flows require simultaneous capture/playback, a physical playback
reference, and an evidenced AEC implementation. A half-duplex demo may prove
basic audio but cannot certify duplex conversation.

## 4. Integrate XiaoTai

Keep one process-wide TiRTC lifecycle and reuse the stable product architecture:
Router -> Arbiter -> Coordinator. SDK callbacks copy bounded events and return;
one state-owning task performs HTTP/MQTT, connection lifecycle, generation
checks and monotonic deadlines.

Put LCD/touch, microphone, codec, amplifier, audio DMA, camera, buttons, memory
pools and AEC behind a Beken board adapter. Keep service discovery, credentials,
stream IDs, negotiated formats and H5/AI/CALL/VOIP state outside board code.

First prove business protocol behavior with the repository's Linux C reference
when it is available. Then bind the pinned Beken TiRTC library/header and build
contract. If no compatible Beken TiRTC binary exists, report `BLOCKED_SDK_ABI`;
do not substitute an ESP32 archive or claim source compatibility.

For BK7258 TiRTC product work, run the case-study gates for AP/CP ownership,
toolchain and TLS ABI identity, clock/signing order, exact HTTP methods,
asynchronous credential lifetime, failed-connection draining, internal-SRAM
headroom and capability-report truthfulness. A successful link is not an ABI or
runtime-media pass.

## 5. Build and verify

Build with the exact vendor toolchain and board project. Record the application
artifact path, version, byte size and SHA-256. Flash only after the user names
the exact device and authorizes it; preserve factory partitions by default.

Re-run the diagnostic report in the same product firmware because standalone
probe results do not prove final memory margin or driver coexistence. Verify
startup, network/onboarding, local media, each requested XiaoTai flow, session
switching/recovery, weak network, and stability separately. Bind runtime results
to the exact artifact SHA-256 and mark each `PASS`, `FAIL`, or `SKIP`.

Return the pinned SDK/BSP revision, probe report, contradictions, capability
matrix, integration changes, exact artifact identity, HIL results, and remaining
blockers. Promote a board profile for reuse only after the exact PCB revision
and its required active probes pass.

## Security and logging boundary

Keep device keys, Wi-Fi passwords, MQTT/WHIP tokens, certificates, calibration
data, MAC-derived identifiers, captured user audio and captured logs outside
source control and generated reports. Use the conventional `ERROR`, `WARN`,
`INFO`, `DEBUG` levels. The LCKFB XiaoTai development project defaults to
`DEBUG`, which prints complete HTTP, MQTT and TiRTC/WHIP inputs and results,
including authorization values. Switching to `INFO` suppresses those complete
network payloads. Handle DEBUG output as sensitive development data. Downloads,
account access, flashing, erasing, factory-partition changes and publishing a
reusable board profile retain separate authorization.

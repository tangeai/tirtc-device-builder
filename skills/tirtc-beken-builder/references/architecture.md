# BK7258/BK7259 XiaoTai architecture

This is the implementation plan delivered with the Skill.

## Platform boundary

Keep Beken in an independent Skill because its SDK, AP/CP image layout,
toolchain, partitions, media drivers and binary ABI differ from ESP32. Reuse
Hardware IR ideas, evidence grades, the business state model and acceptance
levels; do not reuse ESP-IDF board code or an ESP32 TiRTC archive.

BK7258 multimedia work starts from official `bk_avdk_smp`. Pin a formal
`release/v3.1.1.x` tag and match the upper solution tag. Use the moving
`release/v3.1.1` branch only to evaluate newer maintenance changes. Select
BK7259 from its own official support matrix and release line.

## Diagnostic pipeline

```text
documents/schematic/BSP declaration
               -> compiled driver registry
               -> read-only runtime probe
               -> bounded active tests
               -> probe-report.json
               -> UI/media/business capability matrix
               -> Beken adapter + XiaoTai runtime
               -> artifact-bound HIL
```

Use `unknown`, `declared`, `detected`, `measured`, `verified`, and
`unsupported`. Documentation never becomes runtime proof. Preserve
contradictions and bind active evidence to exact board and firmware identity.

## Product decisions

- A verified display with verified touch may expose a touch UI.
- A verified display without verified touch exposes status, QR or animation;
  it has no click targets.
- Buttons are used only when the physical controls and intent map are verified.
  Otherwise select voice/headless interaction.
- Audio-only XiaoTai remains valid without a display.
- AI conversation and call/VoIP require simultaneous capture/playback, a real
  playback reference and AEC verified in far-end, near-end and double-talk.

Flash detection reports JEDEC identity, physical bytes and separately usable
application-partition bytes. Memory reports internal SRAM and PSRAM separately,
including boot free, minimum free and largest block where supported. Repeat
measurements in the final firmware's worst requested session.

## Integration seam

Stable modules own provisioning/binding, service discovery, one TiRTC lifecycle,
HTTP/MQTT, stream contracts, Router -> Arbiter -> Coordinator, generations and
deadlines. The Beken adapter owns LCD/touch, audio/camera DMA, codecs, amplifier,
buttons, memory pools and the AEC reference path. Callbacks enqueue bounded
copies; the state-owning task performs lifecycle and network work.

Before porting, obtain a TiRTC header/library or source package matching the
Beken CPU ABI, compiler, C library, RTOS and TLS/network stack. With no matching
package, diagnosis may complete but integration is `BLOCKED_SDK_ABI`.

## Delivery stages

1. Run Doctor against the pinned SDK.
2. Add the supplied v3.1.1 read-only probe component and board hooks.
3. Run LCD/touch/capture/playback/duplex active tests and assess the JSON report.
4. Prove business protocols with the Linux C reference.
5. Port the Beken adapter and compatible TiRTC package.
6. Build, hash, and rerun resource/probe measurements in the final image.
7. With explicit authorization, flash the exact board and verify each requested
   flow, switching, reconnect, weak network and stability.

The shipped implementation is a reusable diagnosis and decision framework. A
concrete board still needs its exact model/PCB revision, BSP, pin map or
schematic, requested businesses and a compatible TiRTC SDK package.

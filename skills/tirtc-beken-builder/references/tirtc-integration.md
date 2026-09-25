# TiRTC integration on Beken

Use this reference when moving from hardware diagnosis to XiaoTai business code.

## Compatibility gate

Before porting, obtain a Beken-targeted TiRTC header, archive/source package and
build contract matching the exact CPU ABI, compiler, C library, RTOS, TLS/network
stack and required callbacks. Record their versions and hashes. An ESP32 library
is not portable evidence. When a compatible package is unavailable, hardware
diagnosis can finish but business integration is `BLOCKED_SDK_ABI`.

## Stable/application boundary

Stable product modules own:

- provisioning, binding, service discovery and secret injection;
- MQTT/HTTP protocol fields and the single TiRTC lifecycle;
- H5/AI/CALL/VOIP routing, session arbitration and recovery;
- stream IDs, negotiated formats, monotonic deadlines and generation checks;
- callback copying into bounded queues.

The Beken adapter owns:

- LCD/touch presentation and product-control intents;
- microphone capture, format conversion, codec/amplifier and playback;
- DMA buffers, clocks, power/reset, resource ownership and AEC reference;
- camera/encoder path when requested;
- board-specific memory pools and realtime task placement.

Do not let a driver callback call TiRTC lifecycle or HTTP APIs. Do not let a
screen widget own a second session state machine.

## Bring-up sequence

1. Prove the requested protocol and state model with the Linux C reference.
2. Bring up network/time/TLS and inject credentials from an untracked source.
3. Start one TiRTC runtime and wait for its documented ready event.
4. Integrate receive/playback first, then capture/uplink, then full duplex/AEC.
5. Add UI/control intents based on the probe-derived product shape.
6. Exercise one business mode at a time, then switching, reconnect and timeout.
7. Re-run the probe/resource snapshot in the final firmware and bind HIL results
   to its SHA-256.

Use the exact selected TiRTC header for lifecycle and callback details; public
documentation is context, not a substitute for the binary's build contract.

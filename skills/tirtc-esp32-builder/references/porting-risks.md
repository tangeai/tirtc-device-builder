# Board-porting risk gates

Read this reference for every new board or failing media bring-up. It defines generic evidence gates; concrete values belong in the board's Hardware IR and adapter.

## Freeze the contract before code

Record the selected video profile, audio formats and stream IDs, duplex/AEC policy, onboarding method, platform-discovery transport, output path, and mutation authorization. Keep unknown values explicit. A server supporting several codecs does not select one for the device.

## Hardware identity and ownership

- Sensor and codec identity: reconcile schematic/BOM names with BSP probes or ID registers. Store every evidenced variant in an allowlist; retain contradictions as issues.
- I2C: select one ESP-IDF driver family for the final image. Audit the linked ELF when third-party components can introduce another family; a conflict bypass is not a resolution.
- I2S/audio: record controller, GPIO, master/slave mode, clocks, DMA, channel/TDM slot to physical-signal mapping, and shared-signal handoff. A codec name or I2C address does not prove the audio path.
- Realtime camera path: record DMA/event queues, task core/priority, and competing Wi-Fi work. Treat queue overflows as scheduling or throughput evidence, then change one variable per HIL comparison.

Turn every discovered invariant that can regress into a focused test or post-link gate. Generate board-specific values with the project; keep the Skill generic.

## Wi-Fi credentials and device binding

Wi-Fi provisioning and ThingConnect binding are separate state machines.

Select one evidenced Wi-Fi credential method from SoftAP, BLE, SmartConfig, secure factory/NVS provisioning, development configuration, or a documented custom path. SoftAP is not mandatory. A board without AP provisioning can reach `READY_TO_PORT` through another available method when credentials remain outside source control and a reprovisioning path is defined.

Development configuration may inject credentials through an untracked sdkconfig, environment, or provisioning artifact. Treat committed plaintext credentials as `BLOCKED`. Never copy SSIDs/passwords into Hardware IR, reports, examples, or source.

Select the binding method from the applicable platform/product contract: verification code, factory-bound identity, development credentials, or a documented custom flow. When verification-code binding is selected, distinguish at least:

- no Wi-Fi credentials;
- Wi-Fi present but no device binding, so the verification-code flow runs;
- stored binding present, so verification is skipped intentionally;
- binding-only reset and Wi-Fi reset.

For every method, keep device credentials outside source control, handle an already stored identity explicitly, and define binding reset/replacement behavior.

## Startup memory, TLS, and transport

Platform service discovery and the TiRTC SDK service endpoint are different settings. Record both. HTTPS requires valid time, DNS, certificate validation, TLS client/TLS 1.2, and enough contiguous internal memory.

Define a conservative static budget before implementation using the locked SDK contract, framebuffer geometry, DMA/queue bounds, task stacks, and an internal-memory reserve. Before claiming runtime margin or tuning TiRTC buffers, measure internal free/largest blocks, PSRAM, frame size distribution, queue watermarks, and send/drop rates on the exact artifact. A larger queue can prevent drops, exhaust startup memory, or add buffer latency. If an authorized HTTP baseline exists, stage transport changes separately from media changes and retain the HTTPS requirements as a pending acceptance item.

## Network and media evidence

Disable Wi-Fi power saving for the realtime baseline unless the product contract says otherwise. Record BSSID, channel, RSSI, reconnect/roaming events, media counters, queue watermarks, camera overflows, internal heap, and largest block. Establish a strong, stable AP baseline before controlled weak-network testing.

Confirm SDK send return semantics and callback payload lifetimes from the selected SDK version. Keep SDK callbacks bounded and copy payloads before returning.

## Artifact discipline

Record BIN/ELF SHA-256 for every build used in HIL. Runtime evidence applies only to the exact artifact. Diagnose one failing invariant, make the smallest correction, rerun that layer, and preserve the comparison in the report.

# Board-porting risk gates

Read this reference for every new board or failing media bring-up. It defines generic evidence gates; concrete values belong in the board's Hardware IR and adapter.

## Freeze the contract before code

Record the selected video profile, audio formats and stream IDs, duplex/AEC policy, onboarding method, platform-discovery transport, output path, and mutation authorization. Keep unknown values explicit. A server supporting several codecs does not select one for the device.

## Hardware identity and ownership

- Sensor and codec identity: reconcile schematic/BOM names with BSP probes or ID registers. Store every evidenced variant in an allowlist; retain contradictions as issues.
- I2C: select one ESP-IDF driver family for the final image. Audit the linked ELF when third-party components can introduce another family; a conflict bypass is not a resolution.
- I2S/audio: record controller, GPIO, master/slave mode, clocks, DMA, channel/TDM slot to physical-signal mapping, and shared-signal handoff. A codec name or I2C address does not prove the audio path.
- Realtime camera path: record DMA/event queues, task core/priority, and competing Wi-Fi work. Treat queue overflows as scheduling or throughput evidence, then change one variable per HIL comparison.

Distinguish the camera driver's event task from an adapter-owned software
JPEG/H.26x task. Core isolation of the driver does not prove that a CPU-bound
encoder is isolated. On ESP32-S3, code using floating point can cause an
unpinned task to become pinned to the first core where it uses the FPU; AEC and
other DSP tasks therefore need intentional affinity when they would otherwise
land on the Wi-Fi core. A DMA-fed loop or software encoder that can remain
continuously runnable must block on a queue/semaphore or yield at a bounded
frame boundary. Keep the idle-task watchdog enabled, and expose maximum
processing time plus deadline misses instead of hiding starvation by widening
or disabling the watchdog.

Turn every discovered invariant that can regress into a focused test or post-link gate. Generate board-specific values with the project; keep the Skill generic.

## Wi-Fi credentials and device binding

Wi-Fi provisioning and ThingConnect binding are separate state machines.

Select one evidenced Wi-Fi credential method from SoftAP, BLE, SmartConfig, secure factory/NVS provisioning, development configuration, or a documented custom path. SoftAP is not mandatory. A board without AP provisioning can reach `READY_TO_PORT` through another available method when credentials remain outside source control and a reprovisioning path is defined. When SoftAP is selected, implement and record the fixed [SoftAP product contract](hardware-ir.md#softap-product-contract).

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

Treat PSRAM framebuffer placement, direct peripheral DMA into PSRAM, and an
internal-DMA staging buffer as three separate facts. PSRAM capacity does not
prove DMA compatibility or frame integrity for a sensor/pixel format. Promote
direct PSRAM DMA only after artifact-bound HIL checks image boundaries and line
integrity; otherwise retain the evidenced staging path and budget its internal
DMA reserve explicitly.

## Network and media evidence

Disable Wi-Fi power saving for the realtime baseline unless the product contract says otherwise. Record BSSID, channel, RSSI, reconnect/roaming events, media counters, queue watermarks, camera overflows, internal heap, and largest block. Establish a strong, stable AP baseline before controlled weak-network testing.

Confirm SDK send return semantics and callback payload lifetimes from the selected SDK version. Keep SDK callbacks bounded and copy payloads before returning.

## Repeated or duplicated downlink audio

Do not label a build as a fix merely because it adds logs or makes the symptom
less frequent. First produce a self-identifying reproduction build, then count
the same frame across four boundaries: TiRTC receive callback, accepted queue
item, playback dequeue, and codec/I2S write. Include mode and connection
generation, stream/media type, payload length, bounded queue depth/drop counters,
and an available transport sequence or timestamp. Sample payload hashes only as
diagnostic evidence; do not blindly discard equal hashes because silence or
legitimately repeated encoded frames may be identical.

Carry one local trace ID from the accepted callback through queue and playback,
and record write offset, requested bytes, returned bytes, and cumulative bytes.
Multiple codec/I2S writes are valid when a frame is deliberately chunked or a
partial write advances the offset; a local duplication exists only when the
same byte/sample range is committed more than once or cumulative output exceeds
the frame's decoded contract. Repeated callbacks with the same available
transport identity point upstream or into SDK delivery. Unique downlink frames
heard repeatedly require checking resampling, DMA/I2S replay and acoustic
feedback separately. On stop/reconnect, reject stale generations and drain or
invalidate queued audio. Verify the correction with repeated AI sessions, rapid
stop/start, delayed callbacks and H5 recovery against the exact reproduction and
candidate-fix firmware identities.

## Artifact discipline

Follow [firmware-delivery.md](firmware-delivery.md). Record the explicit firmware
version, application-BIN SHA-256 and descriptor/full ELF SHA-256 for every build
used in HIL. Runtime evidence applies only to the exact artifact. Diagnose one
failing invariant, make the smallest correction, rerun that layer, and preserve
the comparison in the report.

Local intermediate snapshots may be ignored, but the Hardware IR, semantic
contracts, `dependencies.lock`, custom partition input, and the artifact named
by retained build evidence must survive the chosen export mechanism. Broad
`*.json`, `*.csv`, or `artifacts/` ignore rules are invalid when they hide an
untracked required input; `project_portability.py --export` checks this when the
project is inside a Git worktree.

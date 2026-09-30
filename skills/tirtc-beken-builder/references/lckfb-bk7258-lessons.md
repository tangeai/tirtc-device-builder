# LCKFB BK7258 XiaoTai lessons

Use this case study for BK7258 XiaoTai/TiRTC ports and reviews. It distils the
failures fixed in `lckfb-bk7258-xiaotai` through source commit `6ec080f`. These
are gates, not a generic board profile: retain the decisions, but use the exact
numbers only when the target matches the identity below.

## Identity gate

The reproducible public SDK baseline is:

- default LCKFB BK7258 board;
- official Beken Gitee repository `bekencorp/bk_avdk_smp`, tag
  `release/v3.1.1.8`, commit
  `1cfd56af09a3cb6470f35f1e0c604035ed1b6ee7`;
- GCC Arm None EABI 10.3.1, Cortex-M33, hard-float;
- TiRTC-Nano 2.5.0 `mini`, BK7258 hard-float archive, SHA-256
  `47e26827ca2419084163e3656dca4d6e508e433381784e9c03f232d3dbaa4171`;
- TiRTC SSL and DTLS disabled for the validated deployment, with remaining
  crypto references resolved by the SDK PSA Mbed TLS 3.5.2 component and no
  application-vendored compatibility archive;
- AP + CP + bootloader package and 16 MiB PSRAM.

The locally delivered folder named `bk_avdk_smp_v3.1.1.8_20260605` contains a
private Tange component and changes to audio, DVP, H.264, lwIP, build options and
project configuration. It is useful only as implementation and fault-history
evidence. Do not identify it as the public tag, use it for SDK checksums, or make
it the default Kit source.

Hash every TiRTC or compatibility archive actually linked and record the SDK commit, compiler,
float ABI, libc/RTOS and partition maps. AP-only or CP-only output is diagnostic;
the deliverable is the combined package. A different value makes a new artifact
that must pass link, signaling/WHIP and hardware validation again. Do not infer
a TLS recipe from the version name: the older 2.3.0 artifact required a separate
compatibility choice, while this validated 2.5.0 artifact uses the SDK PSA path
with TiRTC SSL/DTLS disabled.
Treat the AP and CP CMake caches as part of the SDK identity: both the cached
toolchain path and `beken-armino_SOURCE_DIR` must point inside the selected
official checkout. Reject or clean a cache created by the local modified SDK;
otherwise a nominally successful package can silently mix SDK implementations.

## Board truth gate

The demonstrated LCKFB board uses a 320x240 ST7789V2 SPI display in landscape,
an active-low KEY on GPIO7, onboard microphone/speaker paths, an 8 MiB Flash and
16 MiB PSRAM. It has no fitted touch controller. The optional FT6336 code and
simulated-I2C GPIO42/43 profile describe a later product board; their presence
in the source is not evidence of touch on the LCKFB board.

Check the actual LCD bus/pin profile before debugging pixels, then validate
panel rotation and touch rotation independently. On this board expose status,
AI and call state plus the verified KEY actions; keep touch-only contact, room
and settings navigation disabled.

## Resource gate

Physical capacity did not predict product viability:

- 8 MiB Flash was constrained by the AP code partition, not total Flash. The
  demonstrated layout uses 1904 KiB AP code, 1360 KiB CP code and a 680 KiB
  resource partition; a full roughly 1 MiB CJK font still does not fit the
  intended UI budget. Use a product glyph subset and measure the linked image.
- TiRTC/DTLS needs internal SRAM and sufficiently large contiguous blocks;
  free PSRAM does not replace them. The project reclaimed SRAM by reducing the
  single-session lwIP heap to 80 KiB and TCP send/window sizes to 22 MSS, then
  measured the final workload. Those values are evidence for this product, not
  defaults for every board.
- Reserve the roughly 80 KiB DVP/H.264 controller block before network/TiRTC
  fragmentation. Place eligible supervisor/task storage in PSRAM while keeping
  DMA/internal-only objects in the correct region.
- Size deep WebClient/TLS call stacks from high-water evidence. Move large URL,
  authorization and credential buffers off the control-task stack with bounded
  heap ownership. The demonstrated control and bootstrap tasks required more
  headroom than the original 8 KiB assumptions.
- Keep `CONFIG_LWIP_MEM_STATS` and `CONFIG_LWIP_MEMP_STATS` enabled when the
  selected AVDK allocator references their fields; removing apparently unused
  statistics can break the build.

Report boot, post-driver and worst-session internal free/minimum/largest block,
PSRAM free/minimum/largest block and every static partition/image size. Reject
the build when only aggregate free bytes are known.

## Platform and protocol gate

Lock these semantics with host contract tests instead of rediscovering them on
hardware:

- synchronize network time in the current boot before signed requests or
  TiRTC startup; bridge newlib `_gettimeofday()` to the AON RTC when the SDK
  otherwise links the failing libnosys stub;
- preserve the platform's exact MAC text/client identity and route product APIs
  through the discovered `device`, `ai`, `call` and `voip` services;
- preserve HTTP method and body identity: the device-token operation is an
  empty-body POST, not GET and not `{}`. In the demonstrated AVDK WebClient,
  `webclient_post(..., NULL, 0)` also requires explicit response handling;
- configure the send buffer before `TiRtcInit`, initialize/start one TiRTC
  process, and pass SDK option string lengths with the exact convention used by
  the matching headers/reference; lock the convention with the selected archive
  instead of carrying a value from an older delivery;
- treat a positive `TIRTC_OPT_TGTRP_POLL_TIMEOUT` return as the applied timeout,
  not a failure. A false retry loop repeatedly initialized/uninitialized SDK
  task state;
- retain WHIP peer descriptors and bearer tokens in bounded storage until the
  asynchronous callback completes. Pointers into a freed JSON tree are invalid;
- keep one outgoing connect in flight. A failed or stale callback that returns a
  connection handle must disconnect/drain that handle before another attempt;
  generation and monotonic-deadline checks prevent late callbacks reviving an
  expired owner.

Service URL schemes are a product/deployment contract. Preserve the exact
descriptor returned for the operation that consumes it; apply any HTTP/WHIP
normalization only when the pinned platform and TiRTC package require and test
it. Do not generalize this case study into a universal plain-transport rule.

## Media and capability gate

Build an explicit matrix per product mode. The 2026-09-29 validated BK7258
contract is:

| Mode | Device uplink | Device downlink/subscription | Codec | Uplink gate |
|---|---|---|---|---|
| H5 STREAM | audio 10, video 11 | audio 14, video 15 | G.711 A-law, 8 kHz mono | local uplink subscription state |
| AI | audio 1 | audio 1 | Opus, 16 kHz mono, 20 ms/320 samples | accepted `start_session` |
| WeChat VoIP | audio 0, video 1 | audio 0, video 1 | G.711 A-law, 8 kHz mono; video not advertised here | protocol call-active state |

These stream IDs are a product/platform contract, not universal TiRTC defaults.
Verify them against the live profile API and official protocol before reuse.
Report the complete directional snapshot with `POST /v1/device/profile` before
sessions and after authenticated reconnect. Sending the locally advertised
stream does not imply subscribing to that same number: H5 publishes audio 10
but subscribes to browser talkback audio 14. VoIP publishes and receives audio
0 and must not wait for an optional H5-style subscription callback once the
business protocol has entered call-active state.

Treat TiRTC media and subscription API return values as negative-on-failure
unless the pinned API explicitly documents stricter semantics. Positive returns
were valid success values in this integration; checking `rc != 0` produced
false failures and muted paths.

SDK callbacks enqueue bounded copies and return. Prewarm the Opus codec,
playback, capture and queues before AI `start_session`, but gate microphone
uplink until the matching acceptance. Retain asynchronous peer descriptors and
tokens until callbacks complete.

AEC is a PCM pipeline property, not an Opus-only feature. Enable it for every
speakerphone full-duplex mode that has a playback reference. Feed the
post-volume PCM actually written to DAC into a bounded reference FIFO and
process aligned 20 ms microphone blocks. Validate far-end-only, near-end-only
and double-talk cases; reference underruns or overruns are release evidence,
not harmless counters. On this BK7258 port Opus encode/decode UsageFaults were
eliminated only after placing measured 40 KiB task stacks in PSRAM; carry the
stack size and high-water evidence rather than the number alone.

For one-way audio or echo, add bounded diagnostic logs that correlate mode,
generation, actual/expected stream ID, packet cadence, mic/reference/output
energy, AEC residual ratio and reference FIFO under/overruns. Reject or count
unexpected streams explicitly. Do not tune AEC until routing and reference
continuity are proven.

A camera-start failure degrades video while leaving an otherwise valid audio
session active.

BK7258 provides H.264 encoding but no demonstrated H.264 hardware decoder. The
AVDK virtual H.264 decoder is NAL inspection/logging, not decoded video. The
validated STREAM direction is native H.264 1280x720 at 10 fps uplink plus
full-duplex audio. Report call/VoIP as audio-only until their video path passes.
For local remote-video display, first prove a platform-negotiated 320x240
JPEG/MJPEG path and hardware JPEG decode; otherwise require server transcoding
or another SoC.

Capability JSON must describe only implemented paths using fields accepted by
the live profile API. A camera driver, an encoder block or TiRTC `on_video`
callback alone does not justify bidirectional-video advertising.

## Release gate

Require a host contract test plus artifact-bound HIL. At minimum verify:

- exact archive hashes, ABI/config/partition invariants and AP-only TiRTC
  ownership;
- provisioning, binding, clock, signed login and one complete capability report;
- the exact mode matrix in the reported profile plus actual/expected stream
  diagnostics; first uplink/downlink audio frames and first H.264 frame;
- H5 full duplex on 10/14, AI Opus full duplex on 1, and VoIP full duplex on 0;
- far-end-only, near-end-only and double-talk AEC evidence using the real DAC
  reference, with bounded underrun/overrun counts;
- ten AI enter/exit cycles after background polling starts, with no UsageFault,
  HardFault, reboot, leaked media owner or permanent busy state;
- camera failure with audio preserved, two consecutive remote-view sessions,
  connect/confirmation timeouts and late-callback rejection;
- minimum/largest internal heap and task stack high-water during signaling,
  Opus/AEC, camera and full-duplex overlap.

Use conventional `ERROR`, `WARN`, `INFO`, `DEBUG` levels. The checked-in
development configuration defaults to `DEBUG` and prints complete HTTP, MQTT
and TiRTC/WHIP inputs and results, including authorization values, so developers
can reproduce protocol failures. Switching to `INFO` logs failures, recovery and
state transitions but not complete network inputs or responses.
Contract tests must keep those full-payload format strings behind `BK_LOGD` or
an equivalent DEBUG guard and reject them at INFO/WARN/ERROR. Treat DEBUG logs as
sensitive development artifacts and keep them out of source control.

## Field-log triage gate

Reconstruct a failure by monotonic device time and session generation. Terminal
receive timestamps can batch output and do not establish firmware ordering.
Separate these layers before changing code:

- transport success from business success: HTTP 200 can still carry a rejected
  business code such as an offline target;
- semantic completion from connection closure: TiRTC `-40008` is normal only
  for the same generation after an explicit hangup or `end_session`; otherwise
  retain it as an error;
- locally buffered AI tail from unsent platform audio: after `end_session`, gate
  uplink and drain queued playback before teardown. If the platform closes in
  less than one negotiated audio-frame interval, firmware cannot recover audio
  that never arrived. Require the platform to send the complete final utterance
  before the end command and transport close;
- worker cleanup text from a processor crash: an SDK thread-exit warning alone
  is not reboot evidence. Require a Fault/watchdog record or a new boot sequence;
- touch-controller I/O failures from media faults: diagnose FT6336 read errors,
  invalid touch IDs and missing UP events at the board adapter. Submit dangerous
  tap actions once on DOWN and preserve DOWN/UP pairing for PTT.

For room exit, require all three observable results: the leave API succeeds,
local media closes, and the refreshed assignment is absent. A page transition
alone does not prove that the device left the room. For contact shortcuts,
verify the selected contact class as well as list position; a touch-home WeChat
shortcut and a physical `contacts[0]` shortcut are distinct product intents.

Lock each corrected business rule in the platform-neutral product tests and the
adapter ordering in a board contract test. Use the repository's documented
test entrypoint after locating it; do not invent a generic
`tools/run_host_tests.sh` path across projects.

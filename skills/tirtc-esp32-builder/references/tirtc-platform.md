# TiRTC and ThingConnect platform contract

Read this reference when integrating the C SDK, selecting an ESP32 target, or
implementing H5, AI, device-call or WeChat VoIP.

## Authoritative sources

- TiRTC documentation: <https://docs.tange.ai/products/tirtc/>
- C API: <https://docs.tange.ai/products/tirtc/api-reference/c.html>
- C SDK integration: <https://docs.tange.ai/products/tirtc/guides/sdk-integration/c.html>
- ESP32-S3 notes: <https://docs.tange.ai/products/tirtc/guides/integration-notes/espressif/esp32-s3.html>
- ESP32-P4 notes: <https://docs.tange.ai/products/tirtc/guides/integration-notes/espressif/esp32-p4.html>
- ThingConnect reference platform: <https://github.com/tangeai/tirtc-server-example>
- Demo platform: <https://demo-open.tange-ai.com/>

Use the locked SDK header/build contract and a pinned ThingConnect commit during
generation. Public pages explain the contract but do not replace the exact files
used by a build.

## SDK lifecycle

TiRTC is one process-wide runtime. The exact selected header governs API and
option availability. For SDK 2.3.0 the important order is:

1. Set `TIRTC_OPT_MAX_SEND_BUFFER` before `TiRtcInit()` when overriding it.
2. Call `TiRtcInit()` once.
3. Set `TIRTC_OPT_DEVICE_SECRET_KEY`, `TIRTC_OPT_CLIENT_ID`, the discovered
   service endpoint, and applicable network options before `TiRtcStart()`.
4. Call `TiRtcStart(device_id, &callbacks)` once and wait for
   `TIRTC_EVENT_SYS_STARTED`; return value zero only accepts the request.
5. Establish or accept connections, then use `TiRtcSendVideoStream()` and
   `TiRtcSendAudioStream()` with the selected complete-frame contract.
6. Stop sessions and connections through deferred lifecycle work before the one
   final `TiRtcStop()` / `TiRtcUninit()` sequence.

The callback table and its context outlive the SDK runtime. Callback payloads
are borrowed; copy required data into bounded application-owned storage before
returning.

## Product features

### H5 live view and talkback

The device starts as a listener, accepts the H5 connection, sends the selected
audio/video streams, receives talkback, and handles refresh/key-frame requests.
Browser rendering and audible talkback are HIL evidence.

### AI intercom

Obtain the current AI connection parameters, connect, send `start_session`,
validate the authoritative session ID and input/output formats, then start
media. Remote or local `end_session` converges through the runtime task and
restores the H5 baseline.

### Device-to-device call

Follow the pinned `device-call.md`: contact authorization, `POST
/v1/call/request`, incoming MQTT routing, accept through `POST
/v1/call/device/info`, reject/cancel/hangup, room recovery and `TiRtcConnect`.
Expose `call <device_id> [video|audio]` only after those paths and conflict rules
are implemented.

### WeChat VoIP

Follow the pinned `device-voip.md`: report the device media profile, maintain the
authorized contact list, route WeChat MQTT events, and use `POST
/v1/voip/device/call` for device-originated calls. `wxcall [N] [video|audio]`
selects an authorized contact; it is not a direct SDK API. Mini-program
authorization and plugin behavior are separate platform acceptance evidence.

## Simulator before hardware

For the four-feature portfolio, use the pinned Linux C reference implementation
with file-backed media to prove platform credentials, HTTP/MQTT fields,
connection tokens, commands and the session arbiter before replacing media with
board drivers. Record this separately from ESP32 L1-L7 evidence.

The managed ESP32-S3 starter may expose fewer businesses than the full reference
repository. Missing generated modules are implementation work, not permission to
drop a requested feature or call it verified.

## ESP32 targets

The current managed generator and Device Kit automate ESP32-S3. Official SDK
2.3.0 also provides a distinct ESP32-P4 package. P4 needs ESP-IDF 5.5.4, matching
RISC-V toolchain/build contract, PSRAM, and an evidenced network path such as
ESP-Hosted with C6/C61 or Ethernet. P4 and S3 archives are not interchangeable.

Use FreeRTOS tasks, bounded queues and explicit memory capabilities. PSRAM is
suitable for large media, fixed pools and eligible background stacks; internal
RAM remains necessary for DMA descriptors/buffers, ISR-visible state, control
objects and allocations required while flash cache is unavailable.

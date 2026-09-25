# Capability rules

Use this reference after collecting a probe report and whenever the requested
XiaoTai features change.

## UI policy

| Observed capability | Product result |
|---|---|
| Verified display and verified touch | Touch UI may be enabled. |
| Verified display, no verified touch | Status/QR/animation UI; no click targets. |
| Verified buttons with an approved intent map | Limited button UI may be enabled. |
| No verified display | Audio/voice/headless product remains possible. |

Pixel width/height is sufficient for layout selection. Physical diagonal is
informational unless typography or touch-target sizing depends on it.

## Media and business gates

| Feature | Required evidence |
|---|---|
| H5 audio uplink | Verified microphone capture plus a measured PCM format and an implemented conversion to the platform uplink contract. |
| H5 video | Verified camera/encoder path and an output profile accepted by the pinned platform contract. |
| H5 talkback | Verified speaker playback and an implemented platform downlink decoder. |
| AI conversation | Uplink + playback + simultaneous directions + physical playback reference + enabled/tested AEC. |
| Device call | AI-grade duplex media plus the pinned call protocol and unified session arbiter. |
| WeChat VoIP | AI-grade duplex media plus the pinned VoIP protocol, contact authorization and unified session arbiter. |

Return one of:

- `SUPPORTED`: required active evidence and implementation exist.
- `CANDIDATE`: detected hardware exists but final media conversion, build or HIL
  evidence remains.
- `UNKNOWN`: a safe probe or source fact is missing.
- `BLOCKED`: an authoritative incompatibility or missing required path exists.

## Resource gate

Capacity alone is not a product result. For every enabled feature calculate a
static and peak budget for internal DMA-capable SRAM, general SRAM/PSRAM, task
stacks, frame/audio pools, network/TLS, TiRTC buffers and fragmentation margin.
The build may proceed as `CANDIDATE` with a documented budget; `SUPPORTED`
requires measured minimum-free and largest-block margins in the final firmware's
worst requested session.

Never pool all free memory into one number: a large PSRAM region cannot satisfy
an internal/DMA-only allocation.

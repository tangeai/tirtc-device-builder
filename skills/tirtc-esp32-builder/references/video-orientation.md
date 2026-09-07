# Video geometry, orientation and WeChat UI

Use when a video appears sideways, mirrored, cropped/zoomed, or differs between
H5 and WeChat. Keep four independent facts: sensor output, encoded pixels,
device display viewport, and remote player's UI transform. An absent rotate
call does not prove upright pixels: camera mounting can already introduce an
offset. H5 working does not prove the VoIP-mode encoded pixels are identical.

## Locate the transform

Keep the board and an asymmetric upright test card stationary. Use readable
text plus top/left/right marks; rotation alone and rotation plus reflection
are distinct. State only what the screenshot establishes, not where the
transform happened. Avoid repeatedly asking for placement once confirmed.

Compare short **pre-SDK** H264 clips from each affected mode, with the exact
firmware identity and active generation. Start at SPS/PPS plus IDR, decode
without automatic rotation, inspect pixels, and read coded width/height from
SPS (for example ffprobe). Callback dimensions are useful corroboration, not
a substitute for SPS. A truncated printed ELF hash is not a full identity.

- Matching source clips but different displays: inspect SDK/bridge and player
  UI settings rather than globally rotating the camera again.
- Different source clips: inspect mode-specific capture, crop, encoder input
  and profile transitions first.
- One correctly oriented receive direction says nothing about the opposite
  direction. Apply and test corrections at the intended boundary only.

Retain separate claims for observed pixels, verified source configuration,
successful compilation, and post-change hardware observations.

## Geometry and resources

For a full-frame 90-degree rotation, exchange width/height. A 1280x960 sensor
frame becomes 960x1280; preserving complete pixels is not the same as forcing
a landscape aspect ratio. Validate encoder width AND height limits, alignment,
crop coordinates in input axes, scale factors, clamp logic, direct-input
bypasses, and reserved-resource matching including rotation. Budget an extra
output surface and conversion time. PPA angles in the ESP-IDF P4 driver are
counterclockwise; check the selected header instead of sharing enum values
with a clockwise UI API.

Treat a conservative reference profile as policy, not silicon capacity. Verify
the installed sensor's native modes and actual output; selecting an 800x640
mode and taking its central 640x480 narrows field of view even without a
digital zoom setting. Disable or expose automatic resolution fallback when
the product requires an exact output. Keep H5/phone encode capability separate
from a peer P4's software H264 decode limits.

## WeChat profile contract

Checked 2026-09-07 against the primary
[profile API](https://github.com/tangeai/tirtc-server-example/blob/main/thing-connect/api-reference.md#post-v1voipdeviceprofile)
and [VoIP guide](https://github.com/tangeai/tirtc-server-example/blob/main/thing-connect/device-voip.md).
These URLs track main: pin/recheck the selected platform revision before a
new integration. Do not infer protocol absence from an older board example.

| Field | Boundary / constraint |
| --- | --- |
| `screen_width`, `screen_height` | Actual device display region, not uplink coded dimensions |
| `camera_rotation` | Additional clockwise mini-program UI angle, one of 0/90/180/270; default 0 |
| `aspect_ratio` | Device video's width/height, positive; default 4/3 can be wrong for portrait output |
| `hor_mirror`, `vert_mirror` | Mini-program horizontal/vertical reflection; defaults false |
| `object_fit` | Mini-program `fill` or `contain`; default fill |
| `video_res_mode` | Downlink `auto`, `fit_screen`, or `fill_screen`; does not rotate |

The five UI fields do not configure TiRTC encoding. `fit_screen` bounds MJPEG
inside the screen without cropping/upscaling; `fill_screen` can upscale and
center-crop. Both need valid screen sizes; fill requires even dimensions.
Do not silently change a working downlink mode while investigating uplink UI.
The profile JSON must fit 512 bytes. Test actual serialized fields, types and
size, not only log text. Re-report after changes and start a fresh call so the
mini-program consumes updated configuration.

Choose UI angle relative to the already-transformed encoded pixels; avoid
blindly reporting a physical mounting angle. If pixel correction is already
upright, zero additional UI rotation is a hypothesis to test, not an absolute
rule. A observed need for another angle is endpoint-specific evidence: retain
H5/VoIP captures and test the new call before calling it verified. In particular,
the Waveshare experiment's requested 270 is not a universal board default.

## Bounded capture and serial recovery

The packaged `scripts/capture_uplink.py` supports the **XiaoTai video-capture
console protocol**, not arbitrary TiRTC firmware. It does not flash or install
firmware. Source and device-side integration are pinned in the Waveshare
knowledge package; verify `video-capture` exists before use. Host requirements:
Python plus pyserial on POSIX; ffprobe/ffmpeg are optional for decoded PNG.

```bash
python3 <skill-dir>/scripts/capture_uplink.py --port <exact-port> --output <new-path>.h264
```

Use test-card media only, with explicit serial/capture authorization. The
firmware allocates at most 512 KiB PSRAM on demand and copies complete frames
without blocking for a lock or doing file/serial I/O in the encoder callback.
It stops on capacity, generation/size change, or contention. Approximate
two-second duration is not guaranteed; missing SPS/PPS/IDR can leave it empty.
Export is console-task work after stop and disconnect. No network upload.

The helper answers ANSI status/cursor queries (including queries without a
newline), preserves partial serial lines, uses CR and clears stale command
input. It opens the port exclusively where supported, but a read interruption
alone does not distinguish another reader from USB disconnect or reboot.
Check process ownership and USB logs without killing unrelated processes.
Display safe panic/reboot markers rather than dumping credential-bearing logs.

Recovery is explicit: use `--dump-only` to stop then inspect retained capture;
keep nonempty media, release only an inactive empty buffer, and ask the user
to close the H5 page or hang up before exporting. Terminal Enter is confirmation,
not a remote hangup command. Check offsets, length and checksum before writing
new files. Existing H264/PNG/TXT files can indicate a successful prior export:
inspect them or select a new basename instead of deleting them blindly.

Completion: accepted serialized profile, identified coded dimensions and
pre-SDK pixels, plus separate H5 and WeChat display checks. Tool/host tests alone
do not prove camera orientation, serial HIL or call stability.

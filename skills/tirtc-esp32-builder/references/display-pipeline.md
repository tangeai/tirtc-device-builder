# Device display pipeline

Use this reference for tearing, intermittent flicker, stale UI regions, wrong
RGB colors, panel orientation, touch-coordinate mismatch, or UI layouts that do
not fill a new display. Keep panel scan geometry, LVGL logical geometry, pixel
storage order, framebuffer ownership and touch mapping as separate facts.

## RAM-less video panels

ST7701 and similar MIPI-DSI video panels continuously scan a framebuffer and
have no panel RAM that makes a partial write atomic. Identify the buffer being
scanned before writing. A successful `draw_bitmap` call or two allocated frame
buffers does not by itself prevent tearing.

For a partial-rendering double-buffer path, prove all of these invariants:

- LVGL writes only the back buffer; initialization must not assume framebuffer
  zero is free when the controller starts by scanning framebuffer zero.
- Presentation changes the scan buffer at a frame boundary and the old front
  buffer is recycled only after the corresponding VSYNC/refresh completion.
- Before the recycled buffer receives the next dirty regions, carry forward
  every region changed in the presented frame. Alternating two buffers while
  updating only the latest dirty rectangles produces different UI generations,
  seen as intermittent flicker, stale widgets or local corruption.
- A semaphore token must correspond to a refresh after the requested flip.
  Drain earlier periodic VSYNC tokens around the request or use a monotonic
  generation/counter; an already-full binary semaphore is not flip evidence.

Valid implementations include damage carry-forward after VSYNC, a canonical
shadow frame copied into a safe back buffer, or a genuinely full-frame path.
Choose using measured memory bandwidth and audio/video deadlines. LVGL 8.3
software rotation cannot be combined with its `direct_mode` or `full_refresh`
shortcut; inspect the selected LVGL version before choosing a strategy.

## Rotation, color and touch

- A RAM-less panel's fixed native raster can prevent panel-level `swap_xy`.
  With LVGL 8.3 partial buffers, set `sw_rotate=1` before selecting 90/270
  software rotation. `lv_disp_drv_update()` alone does not enable it.
- Treat 90 versus 270 as a physical installation fact. Verify with asymmetric
  corner labels on the exact enclosure; a vendor portrait drawing does not
  decide the product's landscape direction.
- Let one layer own display and touch rotation. When LVGL rotates the display,
  feed the touch driver native panel coordinates and verify all four corners.
  A second manual transform commonly creates a 180-degree mismatch.
- Derive RGB565 byte order across assets, `LV_COLOR_16_SWAP`, the rotation
  buffer and the panel input. A dark-blue word rendered yellow/brown is a useful
  byte-swap signature. Apply one evidenced swap at the framebuffer boundary.

## Layout and video checks

Find design-grid scaling that still uses a predecessor board's fixed width or
height. Scale against the runtime logical display size, including image zoom,
canvas placement, call-video viewport, decoder pools and presentation depth.
Keep camera/encoded-pixel orientation separate from device-display rotation;
read [video-orientation.md](video-orientation.md) for the remote video path.

Hardware acceptance requires static and animated UI, rapid page changes,
subtitles or timers, four-corner touch, solid RGB test colors and sustained
video. Bind the observation to the exact application BIN hash. Compiler success
does not verify VSYNC ownership, physical rotation or color order.

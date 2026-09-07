# Existing-project media and resource review

Use for missing remote video, allocation failures, task leaks, slow UI or call
switching. This is a focused diagnostic route, not a requirement to redo board
intake, replay every simulator flow or regenerate a working product.

## Establish a narrow baseline

Record business baseline and hardware reference separately. Keep the user's
contacts, call arbitration, onboarding and UI semantics in the former; borrow
drivers, capture and codec resource ownership from the latter. Read the matched
knowledge package's source map, compare pinned commits and relevant dirty files,
then inspect only the path under investigation. Reuse prior build evidence only
when artifact identity matches; otherwise label it historical.

## Receive-to-display contract

For each active mode record uplink codec, subscribe ID, downlink codec and
observed receive metadata independently. H5 video-up stream 11 remains valid;
it does not establish a universal receive stream ID. Authenticate the active
connection, validate generation and negotiated media, and test actual ingress
with captured non-sensitive frame metadata before changing filters.

Use bounded counters at callback, admission, queue, decoder, converter and
presentation boundaries. Count admission rejection separately from overflow.
`rx>0, decoded=0` is not automatically a codec failure. Test enabling remote
production separately from subscription; protocol commands are SDK/reference
specific, not generic magic constants.

## Resource lifecycle

- Inventory task creation and deletion pairs. ESP-IDF `xTaskCreate*WithCaps`
  requires `vTaskDeleteWithCaps`; ordinary deletion retains its statically
  registered stack/TCB. Confirm the installed IDF implementation. Self-deletion
  may allocate a helper task; under tight internal RAM prefer owner-driven
  cleanup after the worker has stopped. A mock API-pair test is not heap HIL.
- Distinguish free capacity, largest contiguous block, DMA capability and
  reserved-workspace ownership. Stop the old codec owner before reconfiguring
  or acquiring a singleton workspace. Retry cannot repair stale ownership.
- Budget internal RAM and PSRAM independently for idle, handshake, duplex media
  and stop/reconnect overlap. Include codec pools, ingress copies, UI surfaces,
  worker stacks and SDK queues; a retained pool is not a per-call leak.
- Measure receive, decode and presentation cadence independently. A 100 ms UI
  timer caps presentation near 10 fps even if decode runs at 15 fps. Evaluate
  dedicated video presentation and smaller MJPEG latest-frame pools against
  audio deadlines; H264 recovery buffers have different dependencies.

## Completion evidence

Run an actual-code regression for the failing seam. Report build/host tests
separately from hardware. For resource changes, compare post-warmup baselines
over repeated connect/cancel/hangup cycles and a sustained duplex call: heap
free/largest/minimum by capability, task stack low-water marks, queue drops,
decode/present rates and audio starvation. Sample cheaply outside realtime
callbacks; choose intervals for the experiment, not permanent noisy polling.
Unreproduced crashes remain unresolved even if a later call succeeds. Change
one high-risk variable per hardware comparison and retain redacted artifact-
bound results; user-reported video is evidence of video, not AEC or stability.

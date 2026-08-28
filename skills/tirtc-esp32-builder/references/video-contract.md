# Video semantic contract

Use this branch whenever a requested feature sends camera video. Create `board-video-contract.json` inside the generated project from the exact board evidence, selected codec/profile, locked components, Device Kit contract, and adapter design.

The project-local contract must establish:

- the exact camera component and ESP-IDF versions from `dependencies.lock`;
- camera event processing isolation from the configured Wi-Fi core, with both task-core selections verified from resolved configuration rather than assumed defaults;
- selected frame-buffer count and memory location;
- `camera.codec` plus the matching SDK media symbol, and one complete MJPEG JPEG, H.264 access unit, or H.265 access unit per SDK send according to the selected profile;
- stream ID, SDK media symbol, refresh semantics, and send return handling;
- maximum encoded frame enforced before send, TiRTC max send buffer, and a lower backpressure threshold;
- exact accepted sensor identities and rejection of every uncorroborated PID;
- implementation assertions against `sdkconfig.defaults`, resolved `sdkconfig`, adapter source, TiRTC wrapper, and product composition root.

For MJPEG use `complete_jpeg_per_send` and `max_complete_jpeg_bytes`; for H.264/H.265 use `complete_access_unit_per_send` and `max_complete_access_unit_bytes`. The media symbol must match the codec. For the LCKFB V1.0.1 MJPEG profile, a complete JPEG must fit at or below the backpressure threshold, which must remain below the TiRTC max send buffer. Camera event work and Wi-Fi must use different cores. These are project contract values, not board-agnostic Skill defaults.

After `idf.py reconfigure`, run:

```bash
python3 <skill-dir>/scripts/video_contract.py \
  <project>/board-video-contract.json \
  --project <project> \
  --evidence-out <project>/build/video-contract-evidence.json
python3 <skill-dir>/scripts/install_video_gate.py <project>
```

The installer copies the verifier into `tools/` and makes every `idf.py build` depend on it. Set `hardware_resources.video_semantic_contract` to the project-relative contract path and pass `--project` to build assessment.

Compilation without this gate is `COMPILE_PASS / VIDEO_CAPABILITY_BLOCKED`. H5 image display remains L5 and requires runtime evidence bound to the exact artifact.

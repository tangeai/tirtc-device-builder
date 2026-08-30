# Hardware IR

Hardware IR describes one exact board revision and product contract. It is the deterministic handoff from board evidence to capability assessment, generation, build, and HIL reporting.

Create the current schema:

```bash
python3 <skill-dir>/scripts/hardware_ir.py init <output>/hardware-ir.json
```

The initializer creates schema v2. The validator still accepts schema v1 for existing H.264-only projects; update new or materially changed boards to v2.

Schema v1 cannot represent an MJPEG/H.265 selection, semantic-contract paths,
or artifact-bound v2 HIL. If an existing v1 project requests H5 video without
an available H.264 path, migrate it to v2 rather than interpreting the legacy
H.264 assessment failure as a board or platform codec failure.

## Evidence rules

- Give every source a stable `id`, `kind`, `location`, and revision when available.
- Use one resolvable location per source. Accept an IR-relative local path or an explicit `https:`, `http:`, `device-kit:`, `managed:`, `official:`, `user-input:`, or `user-supplied:` locator. Reject absolute machine paths, concatenated multi-source strings, invented schemes, missing local paths, and declared SHA-256 values that do not match the referenced local file.
- Reference source IDs from board facts, selected profiles, onboarding methods, resources, and runtime evidence.
- Use `null` for unknown facts. Retain contradictory values as explicit issues instead of choosing silently.
- Hardware revision `unspecified` is valid during intake but blocks reusable-board readiness.
- Keep requested product features under `features.requested`; desired behavior is not hardware evidence.
- Store concrete sensors, pins, clocks, codecs, slots, and task allocation in this board IR/adapter, never in generic Skill defaults.

Verification levels are ordered:

1. `extracted`: one source.
2. `corroborated`: another authoritative artifact confirms it.
3. `build_verified`: matching implementation builds with the locked toolchain.
4. `hardware_verified`: the local peripheral works on the exact board revision.
5. `hil_verified`: retained for legacy facts; schema v2 feature HIL additionally requires matching artifact evidence.

Use the same fact across phases without overstating it. `corroborated` means authoritative sources establish an implementable design; `build_verified` means the generated source, locked dependencies, compile, or post-link gates establish that implementation; runtime behavior requires matching artifact evidence. For example, a corroborated single-I2C-family field records a dependency plan, while its build-verified form records the final ELF audit.

## Schema v2 contracts

The IR contains:

- exact board identity, module, Flash/PSRAM, ESP-IDF, TiRTC SDK and build contract;
- camera identity evidence plus `video_profiles[]` and `selected_video_profile`;
- audio input/output paths;
- `hardware_resources` for I2C, I2S/GPIO ownership, audio channel mapping,
  full-duplex/AEC capability, camera realtime policy, and memory budget;
- project-relative `hardware_resources.audio_semantic_contract` for every project requesting audio;
- project-relative `hardware_resources.video_semantic_contract` for every project requesting video;
- project-relative `hardware_resources.runtime_semantic_contract` for every generated H5/AI/call/VoIP project;
- `onboarding.wifi_credentials` with selectable SoftAP/BLE/SmartConfig/factory/development/custom methods;
- selectable ThingConnect binding methods plus stored-binding states and reset control;
- requested features;
- optional `runtime_evidence[]`, each bound to a full firmware SHA-256.
- `build_evidence.artifacts[]` containing each accepted BIN/ELF path, byte size, and full SHA-256.

When `ai_talk`, `device_call`, or `wechat_voip` is requested,
`hardware_resources.duplex_audio` must establish simultaneous capture/playback,
an actual playback-reference signal, and an AEC implementation. Unknown values
remain `NEEDS_CONFIRMATION`; a confirmed missing value is `BLOCKED`. Build/HIL
assessment also requires the project audio semantic gate to prove enabled AEC.

The selected Wi-Fi method must be available and corroborated, credentials must remain outside tracked source, and reprovisioning must be defined. A board without SoftAP is valid when another selected method meets those conditions.

The selected video profile controls assessment. An unselected H.264 fallback cannot make an MJPEG target pass, and missing H.264 cannot block an evidenced MJPEG target.

## Artifact-bound HIL

Run the phase gates in order:

```bash
python3 <skill-dir>/scripts/hardware_ir.py assess hardware-ir.json \
  --phase intake --strict
python3 <skill-dir>/scripts/hardware_ir.py assess hardware-ir.json \
  --phase build --project <generated-project> \
  --artifact-sha256 <64-character-sha256> --strict
```

The intake phase returns `READY_TO_PORT`; the build phase returns `BUILD_VERIFIED`. Build assessment only accepts a hash already present in `build_evidence.artifacts[]`, reopens that project-relative artifact to verify its byte size and SHA-256, and reruns the project-local audio, video, and runtime contracts through `--project`. Missing serial or browser access does not block either phase.

Run:

```bash
python3 <skill-dir>/scripts/hardware_ir.py assess hardware-ir.json \
  --phase hil --artifact-sha256 <64-character-sha256> --strict
```

H5 features require matching L5 evidence; AI, device-call and WeChat VoIP
require matching L6 evidence. Evidence from an older firmware remains
provenance but does not verify the current artifact.

## Intake quality

Preferred evidence order:

1. exact schematic/netlist and BOM for the physical revision;
2. official BSP pinned to a commit or release;
3. sensor, codec, amplifier and module datasheets;
4. minimal peripheral projects built for that board;
5. product pages, photographs and community material;
6. artifact-bound boot, media and browser observations.

A schematic establishes connectivity, not driver family compatibility, encoding throughput, acoustic behavior, provisioning usability, network performance, or end-to-end TiRTC operation. Preserve each as a separate fact and verification level.

# Evidence and technical claims

Read this reference when documentation states hardware facts, product
capabilities, media parameters, build requirements, release contents, or test
status.

## Source order

Use the closest authoritative source:

1. Product behavior and protocol contracts in the maintained product source or
   product documentation.
2. Board manifest for identity and build metadata.
3. Hardware IR, schematic, probe report, or vendor primary source for wiring,
   fitted devices, memory, clocks, buses, and power sequencing.
4. Lock files, SDK manifests, compiler output, and build scripts for toolchain
   and dependency versions.
5. Release manifest and checksums for downloadable artifacts and flash layout.
6. Artifact-bound hardware-in-the-loop evidence for runtime claims.

A board manifest is build metadata, not proof that hardware or a product flow
worked. A successful compile is not a hardware validation result. Evidence from
one printed-circuit-board revision does not automatically apply to another.

## Board guide minimum

Each supported board guide should independently explain:

- exact public model and printed-circuit-board revision;
- processor, memory, display, touch, camera, audio, and network specifications;
- product functions and technical media parameters;
- operating system, SDK, compiler, libraries, and locked versions;
- official product page, schematic, and source identity;
- root-level build command and expected artifacts;
- safe flash method, offsets, boot mode, and protected factory data;
- provisioning, binding, and first product experience;
- verification level, artifact identity, limitations, and explicit follow-up
  evidence.

Use `unknown` or a clearly scoped follow-up item when a fact lacks evidence.
Do not fill gaps from a visually similar board or another board using the same
processor.

## Media and session details

For each H5, AI, device-call, WeChat VoIP, or room flow that the project claims,
document the applicable direction and parameters:

- stream identifiers;
- encoding, sample rate, channel count, frame duration, samples and payload
  relationship;
- video format, resolution, frame rate, target bitrate, keyframe/refresh rule;
- AEC input, playback reference, processing frame, delay treatment, and modes
  where AEC is required;
- ownership, readiness, stop, reconnect, and resource-release behavior.

Network packet duration and an AEC processing block are different units. State
both when software splits or aggregates them.

## Release download and flashing

Quick-start pages link to an immutable release or a release selector that makes
board identity explicit. A release bundle should carry its board ID, version,
source revision, files, flash offsets, verification status, and SHA-256 values.
Explain the difference between complete flash images and over-the-air images.

Never infer a flash command from a filename alone. Read the bundle manifest or
the board's authoritative flash guide, and preserve calibration, credentials,
keys, and factory partitions unless the product process explicitly replaces
them.

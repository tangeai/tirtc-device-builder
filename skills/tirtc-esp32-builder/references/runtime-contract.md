# TiRTC runtime protocol contract

Use this gate for every generated H5/AI project. It verifies protocol behavior that is
neither a board clock fact nor a camera fact: service discovery wiring, SDK callback
lifecycle, stream/media metadata, and AI session negotiation.

Copy `assets/tirtc-runtime-contract.example.json` to
`<project>/tirtc-runtime-contract.json`. Keep the file paths project-relative. The
Device Kit generator supplies `platform-media-contract.json`; do not recreate it from
the prompt or replace it with board capability claims.

Run and install the gate before the final build:

```bash
python3 <skill-dir>/scripts/runtime_contract.py \
  <project>/tirtc-runtime-contract.json \
  --project <project> \
  --evidence-out <project>/build/runtime-contract-evidence.json
python3 <skill-dir>/scripts/install_runtime_gate.py <project>
```

The gate requires all of the following:

- discovered `tirtc-srv` is passed to `TIRTC_OPT_SERVICE_ENDPOINT`;
- SDK callbacks copy/queue work and never call Disconnect, Stop, or Uninit;
- H5 streams 10/11/14 and AI stream 1 use the platform media contract;
- downlink accepts only G.711 A-law, 8 kHz, mono metadata before decoding;
- platform video capability includes MJPEG, H.264, and H.265 while the board contract
  selects exactly one;
- AI media starts only after a matching response provides a non-empty session ID and
  authoritative input/output audio formats matching the implemented codec;
- remote `end_session` converges through the runtime control task.

Compilation without this gate is not an H5/AI `BUILD_VERIFIED` result.

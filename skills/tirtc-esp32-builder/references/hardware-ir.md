# Hardware IR

Hardware IR is a generated, reviewable description of one exact board revision. It is the only input consumed by deterministic capability checks. Start from [the example](../assets/hardware-ir.example.json) with:

```bash
python3 <skill-dir>/scripts/hardware_ir.py init <output>/hardware-ir.json
```

## Evidence rules

- Give every source a stable `id`, `kind`, `location`, and revision when available.
- Reference those IDs from `soc`, `toolchain`, `camera`, `audio_input`, and `audio_output`.
- Use `null` for unknown presence, pins, formats, or encoder properties. Empty strings are invalid facts.
- Hardware revision `unspecified` is acceptable during intake but blocks registration as a reusable supported board.
- Keep desired features under `features.requested`; do not encode wishes as hardware facts.
- Record the strongest evidenced verification level, not the intended future state.

Verification levels are ordered:

1. `extracted`: obtained from one source.
2. `corroborated`: confirmed by another authoritative artifact, such as schematic plus BSP.
3. `build_verified`: the matching implementation builds with the locked toolchain.
4. `hardware_verified`: the peripheral works on the exact physical revision.
5. `hil_verified`: the requested H5/AI path passes end to end.

## Minimum facts

The IR contains:

- exact board identity and revision;
- SoC target, module, Flash, and PSRAM;
- ESP-IDF and TiRTC SDK platform/version/build contract plus their verification level;
- camera presence, sensor/interface, and H.264 output/key-frame properties;
- audio input and output presence, interface, codecs, sample rates, and verification;
- requested ThingConnect feature IDs.

Pin and driver details may live in a board adapter manifest referenced from the IR once the adapter exists. Until then, missing pins remain capability issues even if the high-level media path appears possible.

## Intake quality

Preferred input order:

1. exact schematic/netlist and BOM for the physical revision;
2. official BSP pinned to a commit or release;
3. sensor, codec, amplifier, and module datasheets;
4. a minimal project that has been built for the board;
5. product pages, README files, photographs, and community material.

A schematic establishes electrical connectivity, not driver maturity, encoding throughput, acoustic behavior, or end-to-end TiRTC compatibility. Preserve those as separate verification facts.

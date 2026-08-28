# Audio semantic contract

Read this reference whenever a requested feature uses microphone capture or speaker playback. Its purpose is to turn codec clocks, I2S modes, channel mapping, and shared-signal ownership into one deterministic build gate.

## Project contract

Create `board-audio-contract.json` in the generated project. Start from `assets/board-audio-contract.example.json`, but replace every board value and evidence ID from the exact schematic, official BSP/example, datasheet, and locked component source. Keep every path project-relative.

The contract must describe:

- the PCM sample rate, MCLK ratio, resulting MCLK, and every clocked codec driver table;
- capture/playback controller, role, and standard/TDM/DSP/PCM mode;
- TDM enable, slot count/order, physical signal at each slot, selected slot, and mapping evidence when TDM is used;
- shared clock GPIOs, whether directions are simultaneous, and the release/recreate handoff;
- source assertions tying the normalized contract to the actual adapter implementation.

A generic header comment such as “typically 256” is not coefficient evidence. After `idf.py reconfigure` resolves managed components, the selected `(MCLK, sample rate)` pair must exist in every locked codec table named by the contract.

## Mandatory gate

Run the gate before claiming an audio-capable build:

```bash
python3 <skill-dir>/scripts/audio_contract.py \
  <project>/board-audio-contract.json \
  --project <project> \
  --evidence-out <project>/build/audio-contract-evidence.json
```

Then install it into every subsequent `idf.py build`:

```bash
python3 <skill-dir>/scripts/install_audio_gate.py <project>
```

The installer copies the verifier into the project and adds an `ALL` CMake dependency for the ELF. A moved project therefore retains its semantic gate without requiring the Skill installation path.

Set `hardware_resources.audio_semantic_contract` to `board-audio-contract.json`. Build assessment must pass `--project <project>`; the assessor reruns the gate and blocks every requested audio feature when the contract is missing or fails.

## Completion criterion

Audio reaches `BUILD_VERIFIED` only when all of these are true:

1. the contract has at least two authoritative source IDs;
2. its arithmetic and codec table lookups pass;
3. its topology, TDM mapping, and handoff are internally consistent;
4. its adapter assertions pass;
5. the gate is part of the ordinary build;
6. the exact BIN/ELF is hashed after that build.

Compilation without this gate is `COMPILE_PASS`, not audio `BUILD_VERIFIED`.

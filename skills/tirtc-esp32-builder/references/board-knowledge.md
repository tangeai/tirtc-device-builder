# Board knowledge and identity

Use this reference when identifying a board, reusing an existing adapter, or
capturing lessons after bring-up. The registry is curated, versioned input. It
does not train a model or mutate an installed Skill from conversation history.

## Identity boundary

An ESP32 can report its SoC target, revision, Flash/PSRAM, MAC and sometimes its
module. Board firmware can probe camera PIDs, codec chip IDs and other bus
devices. These observations identify components, not necessarily the carrier
board sales model, PCB marking, hardware revision, wiring, power topology or
acoustic path. Obtain those facts from the developer and board documents.

Create a project-local identity file, merge the developer declaration with safe
read-only observations, then query the registry:

```bash
python3 <skill-dir>/scripts/board_registry.py init-identity \
  --output <project>/board-identity.json
python3 <skill-dir>/scripts/board_registry.py match \
  --identity <project>/board-identity.json
```

Use only an `exact` result with `safe_registered_reuse=true` to install a saved
adapter. `probable` can supply hypotheses while missing revision or probe facts
are resolved. `component` can supply component-level risks and driver patterns,
but never GPIO, clock, DMA or adapter values. A conflict creates a new variant.

Exact matching requires vendor, model or alias, hardware revision, SoC/resource
compatibility, and every probe marked `required_for_exact`. Marketing names are
not enough because vendors may substitute sensors or codecs without renaming a
product.

## Knowledge scopes

- `generic`: an ESP32/TiRTC invariant. Promote only after two independent board
  packages support it and a focused regression test enforces it.
- `component`: a sensor, codec, amplifier or library observation. Reuse it on a
  different carrier only as a hypothesis until that board supplies evidence.
- `board`: a fact for one exact package identity. Apply it only to an exact
  match.

Registry package status controls reuse:

- `knowledge_only`: lessons are usable, but the normal new-board intake remains
  mandatory.
- `adapter_verified`: the Hardware IR, adapter, configuration and semantic
  contracts are complete enough for the registered-board workflow.
- `hil_verified`: the reusable package also retains artifact-bound HIL evidence.

An older HIL result is provenance, not proof for a newly built artifact.

## Learning loop

After the final assessment, create a project-local candidate:

```bash
python3 <skill-dir>/scripts/board_registry.py candidate \
  --hardware-ir <project>/hardware-ir.json \
  --output <project>/board-knowledge-candidate.json
```

Review the candidate before promotion. Add exact runtime probes, copy only
portable project-relative adapter/config/contract inputs, classify each lesson's
scope, attach the tested artifact SHA-256 for hardware or HIL claims, and add a
regression test for every generic invariant. Then commit it to a maintained
registry and publish a new Skill version. An installed Skill never edits itself
or promotes an observation automatically.

Keep credentials, MAC-derived identity, device keys, Wi-Fi secrets, tokens and
user media out of identity files, candidates and registries.

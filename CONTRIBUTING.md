# Contributing

Open an Issue before adding a new chip platform so the Skill name, SDK source, redistribution boundary, board evidence, and acceptance levels are explicit.

Keep platform workflows in separate directories under `skills/`. A platform Skill owns its toolchain and board adapter rules; ThingConnect H5, AI, identity, session, and TiRTC protocol behavior remains in the upstream repository.

Before submitting changes, run:

```bash
npm ci --ignore-scripts
npm test
npm pack --dry-run
```

Do not commit precompiled SDK archives, firmware binaries, credentials, private board packages, copyrighted vendor documentation without redistribution permission, or user media.

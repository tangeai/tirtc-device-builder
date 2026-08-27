# Contributing

Open an Issue before adding a new chip platform so the Skill name, SDK source, redistribution boundary, board evidence, and acceptance levels are explicit.

Keep platform workflows in separate directories under `skills/`. A platform Skill owns its toolchain and board adapter rules; ThingConnect H5, AI, identity, session, and TiRTC protocol behavior remains in the upstream repository.

Before submitting changes, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/tirtc-esp32-builder/scripts \
  -p 'test_*.py'

python3 scripts/validate_package.py
```

Do not commit precompiled SDK archives, firmware binaries, credentials, private board packages, copyrighted vendor documentation without redistribution permission, or user media.

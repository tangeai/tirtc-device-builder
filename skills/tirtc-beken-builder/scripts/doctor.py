#!/usr/bin/env python3
"""Read-only environment check for the TiRTC Beken Builder."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_SDK_PATHS = (
    "Makefile",
    "ap/include/driver/flash.h",
    "ap/include/driver/lcd.h",
    "ap/include/driver/tp.h",
    "ap/include/os/os.h",
    "ap/components/bk_voice_service",
)


def inspect(root: Path | None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for tool in ("git", "make", "cmake", "ninja", "python3"):
        location = shutil.which(tool)
        checks.append(
            {
                "name": f"tool:{tool}",
                "status": "PASS" if location else "MISS",
                "detail": location,
            }
        )

    revision = None
    if root is None:
        checks.append({"name": "sdk-root", "status": "MISS", "detail": "use --sdk-root or BK_AVDK_SMP_ROOT"})
    elif not root.is_dir():
        checks.append({"name": "sdk-root", "status": "FAIL", "detail": str(root)})
    else:
        checks.append({"name": "sdk-root", "status": "PASS", "detail": str(root.resolve())})
        for relative in REQUIRED_SDK_PATHS:
            present = (root / relative).exists()
            checks.append(
                {
                    "name": f"sdk:{relative}",
                    "status": "PASS" if present else "MISS",
                    "detail": relative,
                }
            )
        try:
            revision = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            checks.append({"name": "sdk-revision", "status": "MISS", "detail": "not a readable git checkout"})
        else:
            checks.append({"name": "sdk-revision", "status": "PASS", "detail": revision})

    overall = "PASS" if all(item["status"] == "PASS" for item in checks) else "NEEDS_SETUP"
    return {"overall": overall, "sdk_revision": revision, "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", help="path to a pinned bk_avdk_smp checkout")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)
    configured = args.sdk_root or os.environ.get("BK_AVDK_SMP_ROOT")
    result = inspect(Path(configured).expanduser() if configured else None)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for check in result["checks"]:
            print(f"{check['status']:5} {check['name']}: {check['detail']}")
        print(f"OVERALL: {result['overall']}")
    return 0 if result["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

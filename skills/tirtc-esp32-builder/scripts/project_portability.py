#!/usr/bin/env python3
"""Check that a generated TiRTC ESP32 source package can move to another machine."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ABSOLUTE_PATH = re.compile(r"(?:^|[\s\"'])(?:/home/|/root/|[A-Za-z]:[\\/])")
BUILD_INPUT_NAMES = {"CMakeLists.txt", "idf_component.yml", "idf_component.yaml"}
BUILD_INPUT_SUFFIXES = {".c", ".h", ".cmake", ".py", ".sh"}
SKIP_PARTS = {"build", "managed_components", ".git"}


def source_files(project: Path):
    for path in project.rglob("*"):
        relative = path.relative_to(project)
        if not path.is_file() or SKIP_PARTS.intersection(relative.parts):
            continue
        if path.name in BUILD_INPUT_NAMES or path.suffix.lower() in BUILD_INPUT_SUFFIXES:
            yield path


def check_project(project_path: Path, export: bool = False) -> dict[str, Any]:
    project = project_path.expanduser().resolve()
    errors: list[str] = []
    if not (project / "CMakeLists.txt").is_file():
        return {"ok": False, "errors": ["CMakeLists.txt is missing"]}
    if not (project / "dependencies.lock").is_file():
        errors.append("dependencies.lock is missing")
    sdk_required = (
        project / "third_party" / "tirtc" / "include" / "tirtc" / "tiRTC.h",
        project / "third_party" / "tirtc" / "lib" / "libTiRTC.a",
        project / "third_party" / "tirtc" / "manifest" / "build-contract.env",
    )
    missing_sdk = [str(path.relative_to(project)) for path in sdk_required if not path.is_file()]
    if missing_sdk:
        errors.append("bundled TiRTC SDK is incomplete: " + ", ".join(missing_sdk))
    if export and (project / "build" / "CMakeCache.txt").exists():
        errors.append("export source contains build/CMakeCache.txt from another machine")

    for path in source_files(project):
        relative = path.relative_to(project)
        text = path.read_text(encoding="utf-8", errors="replace")
        if ABSOLUTE_PATH.search(text):
            errors.append(f"build input contains a machine-specific absolute path: {relative}")
        if path.name == "CMakeLists.txt" or path.suffix.lower() == ".cmake":
            for number, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("COMMAND ") and ".sh" in stripped:
                    command = stripped[len("COMMAND ") :].lstrip('"')
                    if not command.startswith("bash ") and not command.startswith("${BASH"):
                        errors.append(
                            f"shell gate relies on executable permission: {relative}:{number}"
                        )
    return {"ok": not errors, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument(
        "--export",
        action="store_true",
        help="also reject a carried build/CMakeCache.txt",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check_project(args.project, export=args.export)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print("PASS: project source is relocatable")
    else:
        for error in result["errors"]:
            print(f"FAIL: {error}", file=sys.stderr)
    return 0 if result["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

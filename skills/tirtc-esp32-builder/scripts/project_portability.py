#!/usr/bin/env python3
"""Check that a generated TiRTC ESP32 source package can move to another machine."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ABSOLUTE_PATH = re.compile(r"(?:^|[\s\"'])(?:/home/|/root/|[A-Za-z]:[\\/])")
BUILD_INPUT_NAMES = {"CMakeLists.txt", "idf_component.yml", "idf_component.yaml"}
BUILD_INPUT_SUFFIXES = {
    ".c",
    ".cmake",
    ".csv",
    ".defaults",
    ".env",
    ".h",
    ".json",
    ".lock",
    ".py",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_PARTS = {"build", "managed_components", ".git"}
REQUIRED_PROJECT_INPUTS = {
    "dependencies.lock",
    "hardware-ir.json",
    "sdkconfig.defaults",
}
PARTITION_FILE_RE = re.compile(
    r'^CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="([^"]+)"$', re.MULTILINE
)


def source_files(project: Path):
    for path in project.rglob("*"):
        relative = path.relative_to(project)
        if not path.is_file() or SKIP_PARTS.intersection(relative.parts):
            continue
        if path.name in BUILD_INPUT_NAMES or path.suffix.lower() in BUILD_INPUT_SUFFIXES:
            yield path


def project_file(
    project: Path, value: Any, label: str, errors: list[str]
) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty project-relative path")
        return None
    relative = Path(value)
    if relative.is_absolute():
        errors.append(f"{label} must be project-relative, got {value!r}")
        return None
    resolved = (project / relative).resolve()
    if project != resolved and project not in resolved.parents:
        errors.append(f"{label} escapes project root: {value!r}")
        return None
    return resolved


def load_hardware_ir(project: Path, errors: list[str]) -> dict[str, Any] | None:
    path = project / "hardware-ir.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"hardware-ir.json is invalid: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append("hardware-ir.json root must be an object")
        return None
    return data


def required_project_files(
    project: Path, export: bool, errors: list[str]
) -> set[Path]:
    required = {(project / relative).resolve() for relative in REQUIRED_PROJECT_INPUTS}
    ir = load_hardware_ir(project, errors)
    if ir is not None:
        schema_version = ir.get("schema_version")
        requested = ir.get("features", {}).get("requested", [])
        if schema_version == 2:
            resources = ir.get("hardware_resources")
            if not isinstance(resources, dict):
                errors.append("hardware-ir.json hardware_resources must be an object")
            else:
                contract_fields = ["runtime_semantic_contract"]
                if {"h5_live_audio", "h5_talkback", "ai_talk"}.intersection(
                    requested
                ):
                    contract_fields.append("audio_semantic_contract")
                if "h5_live_video" in requested:
                    contract_fields.append("video_semantic_contract")
                for field in contract_fields:
                    path = project_file(
                        project,
                        resources.get(field),
                        f"hardware_resources.{field}",
                        errors,
                    )
                    if path is not None:
                        required.add(path)
        elif (
            schema_version == 1
            and "h5_live_video" in requested
            and ir.get("camera", {}).get("h264", {}).get("available") is not True
        ):
            errors.append(
                "schema v1 can only export the legacy H.264 video contract; "
                "migrate Hardware IR to schema v2 for MJPEG or H.265"
            )

        if export:
            artifacts = ir.get("build_evidence", {}).get("artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                errors.append(
                    "hardware-ir.json build_evidence.artifacts must retain at least "
                    "one verified deliverable for export"
                )
            else:
                for index, record in enumerate(artifacts):
                    if not isinstance(record, dict):
                        errors.append(
                            f"build_evidence.artifacts[{index}] must be an object"
                        )
                        continue
                    path = project_file(
                        project,
                        record.get("path"),
                        f"build_evidence.artifacts[{index}].path",
                        errors,
                    )
                    if path is not None:
                        required.add(path)

    for config_name in ("sdkconfig.defaults", "sdkconfig"):
        config = project / config_name
        if not config.is_file():
            continue
        text = config.read_text(encoding="utf-8", errors="replace")
        match = PARTITION_FILE_RE.search(text)
        if match:
            path = project_file(
                project,
                match.group(1),
                f"{config_name} custom partition table",
                errors,
            )
            if path is not None:
                required.add(path)
    return required


def git_root(project: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def git_ignored(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--", relative.as_posix()],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def check_project(project_path: Path, export: bool = False) -> dict[str, Any]:
    project = project_path.expanduser().resolve()
    errors: list[str] = []
    if not (project / "CMakeLists.txt").is_file():
        return {"ok": False, "errors": ["CMakeLists.txt is missing"]}
    required = required_project_files(project, export, errors)
    for path in sorted(required):
        if not path.is_file():
            errors.append(
                f"required portable input is missing: {path.relative_to(project)}"
            )
    sdk_required = (
        project / "third_party" / "tirtc" / "include" / "tirtc" / "tiRTC.h",
        project / "third_party" / "tirtc" / "lib" / "libTiRTC.a",
        project / "third_party" / "tirtc" / "manifest" / "build-contract.env",
    )
    missing_sdk = [str(path.relative_to(project)) for path in sdk_required if not path.is_file()]
    if missing_sdk:
        errors.append("bundled TiRTC SDK is incomplete: " + ", ".join(missing_sdk))
    if export and (project / "build").exists():
        errors.append("export source contains a machine-bound build/ directory")
    if export:
        root = git_root(project)
        if root is not None:
            for path in sorted(required):
                if path.is_file() and git_ignored(root, path):
                    errors.append(
                        "required portable input is ignored by Git: "
                        f"{path.relative_to(project)}"
                    )

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

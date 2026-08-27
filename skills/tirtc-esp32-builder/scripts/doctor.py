#!/usr/bin/env python3
"""Diagnose an ESP-IDF and TiRTC ESP32 build environment."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


VERSION_PATTERN = re.compile(r"(?:ESP-IDF\s+)?v?(\d+)\.(\d+)(?:\.(\d+))?", re.I)
CONTRACT_KEYS = {
    "CONFIG_FREERTOS_HZ",
    "CONFIG_FREERTOS_USE_TRACE_FACILITY",
    "CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS",
    "CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS",
}
THING_CONNECT_ENV = "TIRTC_THING_CONNECT_ROOT"
GENERATOR_RELATIVE_PATH = Path("device-sim/scripts/create_esp32_project.py")
DEFAULT_SDK_RELATIVE_PATH = Path(
    "device-sim/sdk/espressif-esp32s3/2.3.0"
)


def check(name: str, status: str, detail: str, required: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "required": required,
        "detail": detail,
    }


def parse_version(text: str) -> tuple[int, ...] | None:
    match = VERSION_PATTERN.search(text)
    if match is None:
        return None
    parts = [int(match.group(1)), int(match.group(2))]
    if match.group(3) is not None:
        parts.append(int(match.group(3)))
    return tuple(parts)


def version_matches(actual: tuple[int, ...] | None, expected: str) -> bool:
    if actual is None:
        return False
    expected_match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.x)?", expected)
    if expected_match is None:
        raise ValueError(f"invalid expected ESP-IDF version: {expected}")
    expected_parts = tuple(
        int(part) for part in expected_match.groups() if part is not None
    )
    return actual[: len(expected_parts)] == expected_parts


def run_version(command: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return completed.returncode, output.strip()


def find_idf(explicit: Path | None) -> tuple[Path | None, str]:
    if explicit is not None:
        return explicit.resolve(), "explicit --idf-py"
    on_path = shutil.which("idf.py")
    if on_path:
        return Path(on_path).resolve(), "PATH"
    idf_path = os.environ.get("IDF_PATH")
    if idf_path:
        candidate = Path(idf_path).expanduser() / "tools" / "idf.py"
        if candidate.is_file():
            return candidate.resolve(), "IDF_PATH"
    return None, "not found"


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def parse_kconfig(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    unset_pattern = re.compile(r"#\s+(CONFIG_[A-Z0-9_]+)\s+is not set")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        unset = unset_pattern.fullmatch(line)
        if unset:
            values[unset.group(1)] = "off"
        elif line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            normalized = value.strip().strip('"')
            values[key] = "on" if normalized == "y" else normalized
    return values


def compare_contract(
    contract: dict[str, str], config: dict[str, str]
) -> list[str]:
    mismatches: list[str] = []
    for key in sorted(CONTRACT_KEYS):
        expected = contract.get(key)
        actual = config.get(key)
        if expected is None:
            mismatches.append(f"SDK contract does not declare {key}")
        elif actual is None:
            mismatches.append(f"project does not explicitly configure {key}={expected}")
        elif actual.lower() != expected.lower():
            mismatches.append(f"{key}: expected {expected}, got {actual}")
    return mismatches


def compiler_name(target: str) -> str:
    names = {
        "esp32s3": "xtensa-esp32s3-elf-gcc",
        "esp32": "xtensa-esp32-elf-gcc",
        "esp32c3": "riscv32-esp-elf-gcc",
        "esp32c6": "riscv32-esp-elf-gcc",
        "esp32p4": "riscv32-esp-elf-gcc",
    }
    return names.get(target, "")


def discover_serial_ports() -> list[str]:
    if os.name == "nt":
        return []
    ports: list[str] = []
    for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*", "/dev/cu.usb*"):
        ports.extend(glob.glob(pattern))
    return sorted(set(ports))


def normalize_thing_connect_root(candidate: Path) -> Path | None:
    """Accept either the ThingConnect directory or its parent repository."""
    resolved = candidate.expanduser().resolve()
    for root in (resolved, resolved / "thing-connect"):
        if (root / GENERATOR_RELATIVE_PATH).is_file():
            return root
    return None


def find_thing_connect_root(
    explicit: Path | None,
    project: Path | None,
    *,
    cwd: Path | None = None,
) -> tuple[Path | None, str]:
    if explicit is not None:
        return normalize_thing_connect_root(explicit), "explicit --thing-connect-root"

    from_environment = os.environ.get(THING_CONNECT_ENV)
    if from_environment:
        return (
            normalize_thing_connect_root(Path(from_environment)),
            THING_CONNECT_ENV,
        )

    search_starts = [path for path in (project, cwd or Path.cwd()) if path is not None]
    seen: set[Path] = set()
    for start in search_starts:
        resolved = start.expanduser().resolve()
        if resolved.is_file():
            resolved = resolved.parent
        for candidate in (resolved, *resolved.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            root = normalize_thing_connect_root(candidate)
            if root is not None:
                return root, f"discovered from {start}"
    return None, "not found"


def resolve_sdk_dir(
    explicit: Path | None,
    project: Path | None,
    thing_connect_root: Path | None,
) -> tuple[Path | None, str]:
    if explicit is not None:
        return explicit.expanduser().resolve(), "explicit --sdk-dir"
    if project is not None:
        bundled = project.expanduser().resolve() / "third_party" / "tirtc"
        if bundled.is_dir():
            return bundled, "generated project"
    if thing_connect_root is not None:
        return thing_connect_root / DEFAULT_SDK_RELATIVE_PATH, "ThingConnect workspace"
    return None, "not found"


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    next_actions: list[str] = []

    checks.append(check("python3", "PASS", sys.version.split()[0]))
    for tool, required in (("git", True), ("cmake", False), ("ninja", False)):
        location = shutil.which(tool)
        status = "PASS" if location else ("FAIL" if required else "WARN")
        checks.append(check(tool, status, location or "not found", required))

    idf_path, idf_source = find_idf(args.idf_py)
    if idf_path is None or not idf_path.is_file():
        checks.append(check("idf.py", "FAIL", "not found in PATH or IDF_PATH"))
        next_actions.append(
            f"Install or activate an official ESP-IDF {args.expected_idf}.x environment, then rerun doctor."
        )
    else:
        command = [str(idf_path), "--version"]
        if idf_path.suffix == ".py" and not os.access(idf_path, os.X_OK):
            command.insert(0, sys.executable)
        returncode, output = run_version(command)
        actual = parse_version(output)
        if returncode != 0:
            status = "FAIL"
            detail = f"{idf_path} failed: {output or f'exit {returncode}'}"
        elif not version_matches(actual, args.expected_idf):
            status = "FAIL"
            detail = f"{output}; expected {args.expected_idf}.x"
        else:
            status = "PASS"
            detail = f"{output} ({idf_source}: {idf_path})"
        checks.append(check("idf.py", status, detail))
        if idf_source == "IDF_PATH" and shutil.which("idf.py") is None:
            checks.append(
                check(
                    "idf activation",
                    "FAIL",
                    "IDF_PATH contains idf.py but the current shell is not exported",
                )
            )
            next_actions.append("Activate the existing IDF_PATH installation; do not install a duplicate copy.")

    compiler = compiler_name(args.target)
    if compiler:
        compiler_path = shutil.which(compiler)
        checks.append(
            check(
                "target compiler",
                "PASS" if compiler_path else "FAIL",
                compiler_path or f"{compiler} not found; ESP-IDF environment may be inactive",
            )
        )
    else:
        checks.append(check("target compiler", "FAIL", f"unsupported target {args.target}"))

    thing_connect_root, thing_connect_source = find_thing_connect_root(
        args.thing_connect_root,
        args.project,
    )
    workspace_status = "PASS" if thing_connect_root else (
        "FAIL" if args.require_workspace else "WARN"
    )
    checks.append(
        check(
            "ThingConnect workspace",
            workspace_status,
            (
                f"{thing_connect_root} ({thing_connect_source})"
                if thing_connect_root
                else (
                    f"not found; pass --thing-connect-root or set {THING_CONNECT_ENV}"
                )
            ),
            required=args.require_workspace,
        )
    )
    if args.require_workspace and thing_connect_root is None:
        next_actions.append(
            "Clone the public ThingConnect repository or pass its absolute path with "
            "--thing-connect-root."
        )

    sdk_dir, sdk_source = resolve_sdk_dir(
        args.sdk_dir,
        args.project,
        thing_connect_root,
    )
    if sdk_dir is None:
        sdk_files: list[Path] = []
        missing_sdk = [
            "SDK location unresolved; pass --sdk-dir, --project, or --thing-connect-root"
        ]
        sdk_detail = missing_sdk[0]
    else:
        sdk_files = [
            sdk_dir / "include" / "tirtc" / "tiRTC.h",
            sdk_dir / "lib" / "libTiRTC.a",
            sdk_dir / "manifest" / "build-contract.env",
        ]
        missing_sdk = [str(path) for path in sdk_files if not path.is_file()]
        sdk_detail = (
            "missing: " + ", ".join(missing_sdk)
            if missing_sdk
            else f"{sdk_dir} ({sdk_source})"
        )
    checks.append(
        check(
            "TiRTC SDK",
            "FAIL" if missing_sdk else "PASS",
            sdk_detail,
        )
    )

    if args.project is not None:
        project = args.project.resolve()
        config_path = project / "sdkconfig"
        if not config_path.is_file():
            config_path = project / "sdkconfig.defaults"
        contract_path = (
            sdk_dir / "manifest" / "build-contract.env"
            if sdk_dir is not None
            else None
        )
        if not config_path.is_file():
            checks.append(
                check(
                    "TiRTC build contract",
                    "FAIL",
                    f"no sdkconfig or sdkconfig.defaults in {project}",
                )
            )
        elif contract_path is None or not contract_path.is_file():
            detail = (
                "TiRTC SDK location is unresolved"
                if contract_path is None
                else f"missing {contract_path}"
            )
            checks.append(check("TiRTC build contract", "FAIL", detail))
        else:
            mismatches = compare_contract(
                parse_env_file(contract_path), parse_kconfig(config_path)
            )
            checks.append(
                check(
                    "TiRTC build contract",
                    "FAIL" if mismatches else "PASS",
                    "; ".join(mismatches) if mismatches else f"matches {config_path}",
                )
            )

    ports = discover_serial_ports()
    if args.serial_port:
        serial = Path(args.serial_port)
        if serial.exists() and os.access(serial, os.R_OK | os.W_OK):
            serial_status, serial_detail = "PASS", f"{serial} is readable and writable"
        elif serial.exists():
            serial_status, serial_detail = "FAIL", f"{serial} lacks read/write permission"
        else:
            serial_status, serial_detail = "FAIL", f"{serial} does not exist"
        checks.append(check("serial port", serial_status, serial_detail))
    else:
        checks.append(
            check(
                "serial discovery",
                "PASS" if ports else "WARN",
                ", ".join(ports) if ports else "no serial device detected",
                required=False,
            )
        )

    overall = "FAIL" if any(
        item["required"] and item["status"] == "FAIL" for item in checks
    ) else "PASS"
    return {
        "overall": overall,
        "expected_idf": args.expected_idf,
        "target": args.target,
        "thing_connect_root": (
            str(thing_connect_root) if thing_connect_root is not None else None
        ),
        "sdk_dir": str(sdk_dir) if sdk_dir is not None else None,
        "checks": checks,
        "next_actions": next_actions,
    }


def print_human(result: dict[str, Any]) -> None:
    for item in result["checks"]:
        suffix = " [required]" if item["required"] else ""
        print(f"{item['status']:4} {item['name']}{suffix}: {item['detail']}")
    print(f"OVERALL: {result['overall']}")
    for action in result["next_actions"]:
        print(f"NEXT: {action}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check ESP-IDF, target tools, TiRTC SDK, project contract, and serial access."
    )
    parser.add_argument("--expected-idf", default="5.5")
    parser.add_argument("--target", default="esp32s3")
    parser.add_argument("--idf-py", type=Path)
    parser.add_argument("--thing-connect-root", type=Path)
    parser.add_argument(
        "--require-workspace",
        action="store_true",
        help="fail when a ThingConnect workspace with the ESP32 generator is unavailable",
    )
    parser.add_argument("--sdk-dir", type=Path)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--serial-port")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = diagnose(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    return 0 if result["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

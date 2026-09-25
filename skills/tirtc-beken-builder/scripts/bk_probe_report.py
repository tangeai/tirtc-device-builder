#!/usr/bin/env python3
"""Create, collect, validate, and conservatively assess BK probe reports."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


PREFIX = "TIRTC_BK_PROBE "
STATES = {"unknown", "declared", "detected", "measured", "verified", "unsupported"}
TESTS = {"pass", "fail", "not_run"}
FEATURES = {
    "h5_audio",
    "h5_video",
    "h5_talkback",
    "ai_talk",
    "device_call",
    "wechat_voip",
}
SECRET_KEYS = {
    "access_key",
    "password",
    "secret",
    "secret_key",
    "ssid",
    "token",
    "wifi_password",
}


def template() -> dict[str, Any]:
    asset = Path(__file__).resolve().parent.parent / "assets" / "probe-report.example.json"
    return json.loads(asset.read_text(encoding="utf-8"))


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("probe report root must be an object")
    return value


def nested(report: dict[str, Any], dotted: str) -> Any:
    value: Any = report
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def validate(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    identity = report.get("identity")
    if not isinstance(identity, dict):
        errors.append("identity must be an object")
    elif identity.get("soc") not in {"BK7258", "BK7259"}:
        errors.append("identity.soc must be BK7258 or BK7259")

    for path in (
        "flash",
        "memory.internal_sram",
        "memory.psram",
        "display",
        "touch",
        "camera",
        "audio.microphone",
        "audio.speaker",
    ):
        item = nested(report, path)
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object")
            continue
        if item.get("state") not in STATES:
            errors.append(f"{path}.state must be one of {sorted(STATES)}")
        if "test" in item and item.get("test") not in TESTS:
            errors.append(f"{path}.test must be one of {sorted(TESTS)}")

    duplex = nested(report, "audio.duplex")
    if not isinstance(duplex, dict):
        errors.append("audio.duplex must be an object")
    elif duplex.get("aec_test") not in TESTS:
        errors.append(f"audio.duplex.aec_test must be one of {sorted(TESTS)}")
    else:
        for name in ("simultaneous", "playback_reference", "aec_available"):
            value = duplex.get(name)
            if value is not None and not isinstance(value, bool):
                errors.append(f"audio.duplex.{name} must be true, false, or null")

    for path in (
        "flash.physical_bytes",
        "flash.mapped_bytes",
        "flash.application_usable_bytes",
        "memory.internal_sram.total_bytes",
        "memory.internal_sram.free_boot_bytes",
        "memory.internal_sram.minimum_free_bytes",
        "memory.internal_sram.largest_free_block_bytes",
        "memory.psram.total_bytes",
        "memory.psram.free_boot_bytes",
        "memory.psram.minimum_free_bytes",
        "memory.psram.largest_free_block_bytes",
        "display.width_px",
        "display.height_px",
        "controls.verified_buttons",
    ):
        value = nested(report, path)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            errors.append(f"{path} must be a non-negative integer or null")

    flash_recognized = nested(report, "flash.recognized")
    if flash_recognized is not None and not isinstance(flash_recognized, bool):
        errors.append("flash.recognized must be true, false, or null")

    requested = report.get("requested_features")
    if not isinstance(requested, list) or any(item not in FEATURES for item in requested):
        errors.append(f"requested_features must contain only {sorted(FEATURES)}")
    elif len(requested) != len(set(requested)):
        errors.append("requested_features must not contain duplicates")

    if not isinstance(report.get("issues"), list):
        errors.append("issues must be an array")

    integration = report.get("integration")
    if not isinstance(integration, dict):
        errors.append("integration must be an object")
    else:
        for name, value in integration.items():
            if value is not None and not isinstance(value, bool):
                errors.append(f"integration.{name} must be true, false, or null")

    artifact = report.get("artifact_sha256")
    if artifact is not None and (
        not isinstance(artifact, str)
        or len(artifact) != 64
        or any(ch not in "0123456789abcdefABCDEF" for ch in artifact)
    ):
        errors.append("artifact_sha256 must be null or 64 hexadecimal characters")

    def find_secrets(value: Any, location: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                here = f"{location}.{key}" if location else key
                if key.lower() in SECRET_KEYS:
                    errors.append(f"secret-bearing field is forbidden: {here}")
                find_secrets(child, here)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                find_secrets(child, f"{location}[{index}]")

    find_secrets(report)
    return errors


def state_of(report: dict[str, Any], path: str) -> str:
    value = nested(report, f"{path}.state")
    return value if isinstance(value, str) else "unknown"


def active_pass(report: dict[str, Any], path: str) -> bool:
    return nested(report, f"{path}.test") == "pass" and state_of(report, path) in {
        "detected",
        "measured",
        "verified",
    }


def absent(report: dict[str, Any], path: str) -> bool:
    return state_of(report, path) == "unsupported" or nested(report, f"{path}.test") == "fail"


def gate(hardware_ok: bool, hardware_absent: bool, implementation: Any) -> dict[str, str]:
    if hardware_absent:
        return {"status": "BLOCKED", "reason": "required hardware path failed or is unsupported"}
    if not hardware_ok:
        return {"status": "UNKNOWN", "reason": "required active hardware evidence is missing"}
    if implementation is True:
        return {"status": "SUPPORTED", "reason": "hardware probe and implementation gate passed"}
    return {"status": "CANDIDATE", "reason": "hardware passed; implementation/build evidence remains"}


def assess(report: dict[str, Any]) -> dict[str, Any]:
    display_ok = active_pass(report, "display") and all(
        isinstance(nested(report, key), int) and nested(report, key) > 0
        for key in ("display.width_px", "display.height_px")
    )
    touch_ok = active_pass(report, "touch")
    mic_ok = active_pass(report, "audio.microphone") and bool(nested(report, "audio.microphone.sample_rates_hz"))
    speaker_ok = active_pass(report, "audio.speaker")
    camera_ok = active_pass(report, "camera") and bool(nested(report, "camera.output_profiles"))
    duplex_ok = all(
        nested(report, path) is True
        for path in (
            "audio.duplex.simultaneous",
            "audio.duplex.playback_reference",
            "audio.duplex.aec_available",
        )
    ) and nested(report, "audio.duplex.aec_test") == "pass"
    sdk_ok = nested(report, "integration.tirtc_sdk_compatible") is True

    matrix: dict[str, dict[str, str]] = {}
    matrix["display_ui"] = gate(display_ok, absent(report, "display"), True)
    matrix["touch_ui"] = gate(display_ok and touch_ok, absent(report, "display") or absent(report, "touch"), True)

    if display_ok and not touch_ok:
        buttons = nested(report, "controls.verified_buttons") or 0
        approved = nested(report, "controls.intent_map_approved") is True
        matrix["recommended_ui"] = {
            "status": "SUPPORTED",
            "reason": "status/voice UI" + (" with approved buttons" if buttons and approved else "; no click targets"),
        }
    elif display_ok and touch_ok:
        matrix["recommended_ui"] = {"status": "SUPPORTED", "reason": "touch UI"}
    else:
        matrix["recommended_ui"] = {"status": "CANDIDATE", "reason": "voice/headless UI"}

    matrix["h5_audio"] = gate(
        mic_ok,
        absent(report, "audio.microphone"),
        sdk_ok and nested(report, "integration.audio_uplink_pipeline") is True,
    )
    matrix["h5_talkback"] = gate(
        speaker_ok,
        absent(report, "audio.speaker"),
        sdk_ok and nested(report, "integration.audio_downlink_pipeline") is True,
    )
    matrix["h5_video"] = gate(
        camera_ok,
        absent(report, "camera"),
        sdk_ok and nested(report, "integration.video_uplink_pipeline") is True,
    )
    duplex_blocked = any(
        nested(report, path) is False
        for path in (
            "audio.duplex.simultaneous",
            "audio.duplex.playback_reference",
            "audio.duplex.aec_available",
        )
    ) or nested(report, "audio.duplex.aec_test") == "fail"
    audio_hw_absent = (
        absent(report, "audio.microphone")
        or absent(report, "audio.speaker")
        or duplex_blocked
    )
    ai_impl = all(
        nested(report, path) is True
        for path in (
            "integration.tirtc_sdk_compatible",
            "integration.audio_uplink_pipeline",
            "integration.audio_downlink_pipeline",
            "integration.session_arbiter",
        )
    )
    matrix["ai_talk"] = gate(mic_ok and speaker_ok and duplex_ok, audio_hw_absent, ai_impl)
    matrix["device_call"] = gate(
        mic_ok and speaker_ok and duplex_ok,
        audio_hw_absent,
        ai_impl and nested(report, "integration.device_call_protocol") is True,
    )
    matrix["wechat_voip"] = gate(
        mic_ok and speaker_ok and duplex_ok,
        audio_hw_absent,
        ai_impl and nested(report, "integration.wechat_voip_protocol") is True,
    )

    requested = report.get("requested_features", [])
    requested_status = {name: matrix[name] for name in requested}
    overall = "READY"
    if any(value["status"] == "BLOCKED" for value in requested_status.values()):
        overall = "BLOCKED"
    elif any(value["status"] == "UNKNOWN" for value in requested_status.values()):
        overall = "NEEDS_PROBE"
    elif any(value["status"] == "CANDIDATE" for value in requested_status.values()):
        overall = "READY_TO_PORT"

    return {
        "schema_version": 1,
        "identity": copy.deepcopy(report.get("identity")),
        "artifact_sha256": report.get("artifact_sha256"),
        "overall": overall,
        "capabilities": matrix,
        "requested": requested_status,
        "issues": copy.deepcopy(report.get("issues", [])),
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_init(args: argparse.Namespace) -> int:
    target = Path(args.output)
    if target.exists() and not args.force:
        print(f"refusing to overwrite existing file: {target}", file=sys.stderr)
        return 2
    write_json(target, template())
    print(target)
    return 0


def command_collect(args: argparse.Namespace) -> int:
    source = Path(args.input)
    candidates: list[dict[str, Any]] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        marker = line.find(PREFIX)
        if marker < 0:
            continue
        try:
            value = json.loads(line[marker + len(PREFIX):])
        except json.JSONDecodeError as exc:
            print(f"ignoring malformed framed report at line {line_number}: {exc}", file=sys.stderr)
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        print(f"no complete {PREFIX.strip()} report found in {source}", file=sys.stderr)
        return 2
    errors = validate(candidates[-1])
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    write_json(Path(args.output), candidates[-1])
    print(f"collected report {len(candidates)} -> {args.output}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    report = load(Path(args.report))
    errors = validate(report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(f"VALID probe-report-v1 sha256={digest}")
    return 0


def command_assess(args: argparse.Namespace) -> int:
    report = load(Path(args.report))
    errors = validate(report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    result = assess(report)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create an empty v1 probe report")
    init.add_argument("output")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)
    collect = commands.add_parser("collect", help="extract the last framed JSON report from a serial log")
    collect.add_argument("input")
    collect.add_argument("output")
    collect.set_defaults(func=command_collect)
    check = commands.add_parser("validate", help="validate a probe report")
    check.add_argument("report")
    check.set_defaults(func=command_validate)
    assessment = commands.add_parser("assess", help="produce a conservative capability matrix")
    assessment.add_argument("report")
    assessment.add_argument("--output")
    assessment.set_defaults(func=command_assess)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

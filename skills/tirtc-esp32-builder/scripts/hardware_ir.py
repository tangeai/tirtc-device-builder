#!/usr/bin/env python3
"""Create, validate, and assess TiRTC embedded Hardware IR files."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


FEATURES = {
    "h5_live_audio",
    "h5_live_video",
    "h5_talkback",
    "ai_talk",
}
VERIFICATION_LEVELS = {
    "extracted": 1,
    "corroborated": 2,
    "build_verified": 3,
    "hardware_verified": 4,
    "hil_verified": 5,
}
READY_STATUSES = {"READY_TO_PORT", "HIL_VERIFIED"}


def load_ir(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Hardware IR does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Hardware IR root must be an object")
    return data


def mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return {}
    return value


def nonempty_string(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")


def positive_int(value: Any, path: str, errors: list[str], allow_zero: bool = False) -> None:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        errors.append(f"{path} must be an integer >= {minimum}")


def nullable_bool(value: Any, path: str, errors: list[str]) -> None:
    if value is not None and not isinstance(value, bool):
        errors.append(f"{path} must be true, false, or null")


def validate_source_refs(
    section: dict[str, Any], path: str, source_ids: set[str], errors: list[str]
) -> None:
    refs = section.get("source_refs")
    if not isinstance(refs, list) or not refs:
        errors.append(f"{path}.source_refs must be a non-empty array")
        return
    for index, ref in enumerate(refs):
        if not isinstance(ref, str) or not ref:
            errors.append(f"{path}.source_refs[{index}] must be a non-empty string")
        elif ref not in source_ids:
            errors.append(f"{path}.source_refs[{index}] references unknown source {ref!r}")


def validate_codec_list(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return
    for index, item in enumerate(value):
        prefix = f"{path}[{index}]"
        codec = mapping(item, prefix, errors)
        nonempty_string(codec.get("name"), f"{prefix}.name", errors)
        rates = codec.get("sample_rates_hz")
        if not isinstance(rates, list) or not rates:
            errors.append(f"{prefix}.sample_rates_hz must be a non-empty array")
        else:
            for rate_index, rate in enumerate(rates):
                positive_int(rate, f"{prefix}.sample_rates_hz[{rate_index}]", errors)
        verification = codec.get("verification")
        if verification not in VERIFICATION_LEVELS:
            errors.append(
                f"{prefix}.verification must be one of "
                + ", ".join(VERIFICATION_LEVELS)
            )


def validate_ir(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    board = mapping(data.get("board"), "board", errors)
    for key in ("id", "vendor", "model", "hardware_revision"):
        nonempty_string(board.get(key), f"board.{key}", errors)

    sources = data.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array")
    else:
        for index, item in enumerate(sources):
            prefix = f"sources[{index}]"
            source = mapping(item, prefix, errors)
            for key in ("id", "kind", "location"):
                nonempty_string(source.get(key), f"{prefix}.{key}", errors)
            source_id = source.get("id")
            if isinstance(source_id, str) and source_id:
                if source_id in source_ids:
                    errors.append(f"duplicate source id {source_id!r}")
                source_ids.add(source_id)

    soc = mapping(data.get("soc"), "soc", errors)
    nonempty_string(soc.get("target"), "soc.target", errors)
    nonempty_string(soc.get("module"), "soc.module", errors)
    positive_int(soc.get("flash_mb"), "soc.flash_mb", errors)
    positive_int(soc.get("psram_mb"), "soc.psram_mb", errors, allow_zero=True)
    validate_source_refs(soc, "soc", source_ids, errors)

    toolchain = mapping(data.get("toolchain"), "toolchain", errors)
    nonempty_string(toolchain.get("framework"), "toolchain.framework", errors)
    nonempty_string(
        toolchain.get("framework_version"), "toolchain.framework_version", errors
    )
    toolchain_verification = toolchain.get("verification")
    if toolchain_verification not in VERIFICATION_LEVELS:
        errors.append(
            "toolchain.verification must be one of "
            + ", ".join(VERIFICATION_LEVELS)
        )
    tirtc = mapping(toolchain.get("tirtc"), "toolchain.tirtc", errors)
    for key in ("platform", "version", "sdk_path", "build_contract"):
        nonempty_string(tirtc.get(key), f"toolchain.tirtc.{key}", errors)
    validate_source_refs(toolchain, "toolchain", source_ids, errors)

    camera = mapping(data.get("camera"), "camera", errors)
    nullable_bool(camera.get("present"), "camera.present", errors)
    h264 = mapping(camera.get("h264"), "camera.h264", errors)
    nullable_bool(h264.get("available"), "camera.h264.available", errors)
    nullable_bool(
        h264.get("key_frame_control"), "camera.h264.key_frame_control", errors
    )
    verification = h264.get("verification")
    if verification not in VERIFICATION_LEVELS:
        errors.append(
            "camera.h264.verification must be one of "
            + ", ".join(VERIFICATION_LEVELS)
        )
    validate_source_refs(camera, "camera", source_ids, errors)

    for name in ("audio_input", "audio_output"):
        media = mapping(data.get(name), name, errors)
        nullable_bool(media.get("present"), f"{name}.present", errors)
        validate_codec_list(media.get("codecs"), f"{name}.codecs", errors)
        validate_source_refs(media, name, source_ids, errors)

    features = mapping(data.get("features"), "features", errors)
    requested = features.get("requested")
    if not isinstance(requested, list) or not requested:
        errors.append("features.requested must be a non-empty array")
    else:
        seen: set[str] = set()
        for index, feature in enumerate(requested):
            if feature not in FEATURES:
                errors.append(
                    f"features.requested[{index}] must be one of "
                    + ", ".join(sorted(FEATURES))
                )
            elif feature in seen:
                errors.append(f"features.requested contains duplicate {feature!r}")
            else:
                seen.add(feature)
    return errors


def codec_requirement(media: dict[str, Any], section: str) -> tuple[str, str, int]:
    present = media.get("present")
    if present is None:
        return "NEEDS_CONFIRMATION", f"{section} presence is unknown", 0
    if present is False:
        return "BLOCKED", f"{section} is not present", 0
    codecs = media.get("codecs", [])
    for codec in codecs:
        if not isinstance(codec, dict) or str(codec.get("name", "")).lower() != "alaw":
            continue
        if 8000 not in codec.get("sample_rates_hz", []):
            continue
        verification = codec.get("verification")
        level = VERIFICATION_LEVELS.get(verification, 0)
        if level < VERIFICATION_LEVELS["corroborated"]:
            return (
                "NEEDS_CONFIRMATION",
                f"{section} A-law 8 kHz path is only {verification}",
                level,
            )
        return "SATISFIED", f"{section} provides A-law 8 kHz", level
    return "BLOCKED", f"{section} has no A-law 8 kHz path", 0


def video_requirement(camera: dict[str, Any]) -> tuple[str, str, int]:
    present = camera.get("present")
    if present is None:
        return "NEEDS_CONFIRMATION", "camera presence is unknown", 0
    if present is False:
        return "BLOCKED", "camera is not present", 0
    h264 = camera.get("h264", {})
    available = h264.get("available")
    if available is None:
        return "NEEDS_CONFIRMATION", "H.264 encoder availability is unknown", 0
    if available is False:
        return "BLOCKED", "H.264 encoder is unavailable", 0
    output_format = h264.get("output_format")
    if output_format is None:
        return "NEEDS_CONFIRMATION", "H.264 output format is unknown", 0
    if str(output_format).lower() != "h264_annex_b":
        return "BLOCKED", "H5 requires H.264 Annex-B access units", 0
    key_frame = h264.get("key_frame_control")
    if key_frame is None:
        return "NEEDS_CONFIRMATION", "key-frame request control is unknown", 0
    if key_frame is False:
        return "BLOCKED", "key-frame requests cannot reach the encoder", 0
    verification = h264.get("verification")
    level = VERIFICATION_LEVELS.get(verification, 0)
    if level < VERIFICATION_LEVELS["corroborated"]:
        return (
            "NEEDS_CONFIRMATION",
            f"H.264 Annex-B path is only {verification}",
            level,
        )
    return "SATISFIED", "camera provides H.264 Annex-B and IDR control", level


def combine_requirements(requirements: list[tuple[str, str, int]]) -> dict[str, Any]:
    reasons = [reason for _, reason, _ in requirements]
    states = {state for state, _, _ in requirements}
    levels = [level for state, _, level in requirements if state == "SATISFIED"]
    if "BLOCKED" in states:
        status = "BLOCKED"
    elif "NEEDS_CONFIRMATION" in states:
        status = "NEEDS_CONFIRMATION"
    elif levels and min(levels) >= VERIFICATION_LEVELS["hil_verified"]:
        status = "HIL_VERIFIED"
    else:
        status = "READY_TO_PORT"
    return {"status": status, "reasons": reasons}


def project_requirements(data: dict[str, Any]) -> list[tuple[str, str, int]]:
    requirements: list[tuple[str, str, int]] = []
    revision = data["board"]["hardware_revision"].strip().lower()
    if revision in {"unknown", "unspecified", "n/a"}:
        requirements.append(
            ("NEEDS_CONFIRMATION", "exact hardware revision is unresolved", 0)
        )
    else:
        requirements.append(
            ("SATISFIED", f"hardware revision is {data['board']['hardware_revision']}", 2)
        )

    target = data["soc"]["target"].strip().lower()
    if target != "esp32s3":
        requirements.append(
            (
                "BLOCKED",
                f"current starter generator supports esp32s3, not {target}",
                0,
            )
        )
    else:
        requirements.append(("SATISFIED", "ESP32-S3 starter is available", 2))

    platform = data["toolchain"]["tirtc"]["platform"].strip().lower()
    expected_platform = "espressif-esp32s3"
    if target == "esp32s3" and platform != expected_platform:
        requirements.append(
            (
                "BLOCKED",
                f"TiRTC platform {platform} does not match {expected_platform}",
                0,
            )
        )
    else:
        requirements.append(("SATISFIED", "TiRTC platform matches target", 2))

    verification = data["toolchain"].get("verification")
    level = VERIFICATION_LEVELS.get(verification, 0)
    if level < VERIFICATION_LEVELS["corroborated"]:
        requirements.append(
            (
                "NEEDS_CONFIRMATION",
                f"toolchain and SDK contract are only {verification}",
                level,
            )
        )
    else:
        requirements.append(
            ("SATISFIED", "toolchain and SDK contract are corroborated", level)
        )
    return requirements


def assess_ir(data: dict[str, Any]) -> dict[str, Any]:
    requested = data["features"]["requested"]
    audio_input = data["audio_input"]
    audio_output = data["audio_output"]
    camera = data["camera"]
    result: dict[str, Any] = {}
    for feature in requested:
        if feature == "h5_live_audio":
            requirements = [codec_requirement(audio_input, "audio_input")]
        elif feature == "h5_live_video":
            requirements = [video_requirement(camera)]
        elif feature == "h5_talkback":
            requirements = [codec_requirement(audio_output, "audio_output")]
        else:
            requirements = [
                codec_requirement(audio_input, "audio_input"),
                codec_requirement(audio_output, "audio_output"),
            ]
        result[feature] = combine_requirements(requirements)
    return {
        "board_id": data["board"]["id"],
        "hardware_revision": data["board"]["hardware_revision"],
        "project_gate": combine_requirements(project_requirements(data)),
        "features": result,
    }


def command_init(args: argparse.Namespace) -> int:
    output = args.output.resolve()
    if output.exists():
        print(f"refusing to overwrite existing file: {output}", file=sys.stderr)
        return 2
    example = Path(__file__).resolve().parent.parent / "assets" / "hardware-ir.example.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(example, output)
    print(f"created Hardware IR: {output}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    try:
        data = load_ir(args.path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    errors = validate_ir(data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"valid Hardware IR: {args.path}")
    return 0


def command_assess(args: argparse.Namespace) -> int:
    try:
        data = load_ir(args.path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    errors = validate_ir(data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    assessment = assess_ir(data)
    print(json.dumps(assessment, ensure_ascii=False, indent=2))
    if args.strict:
        statuses = {
            item["status"] for item in assessment["features"].values()
        }
        statuses.add(assessment["project_gate"]["status"])
        if not statuses.issubset(READY_STATUSES):
            return 3
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create, validate, and assess TiRTC embedded Hardware IR files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a new Hardware IR")
    init_parser.add_argument("output", type=Path)
    init_parser.set_defaults(handler=command_init)

    validate_parser = subparsers.add_parser("validate", help="validate an IR")
    validate_parser.add_argument("path", type=Path)
    validate_parser.set_defaults(handler=command_validate)

    assess_parser = subparsers.add_parser(
        "assess", help="assess requested features against current starter contracts"
    )
    assess_parser.add_argument("path", type=Path)
    assess_parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero unless every requested feature is ready or HIL verified",
    )
    assess_parser.set_defaults(handler=command_assess)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

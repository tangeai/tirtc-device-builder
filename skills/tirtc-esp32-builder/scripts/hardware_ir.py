#!/usr/bin/env python3
"""Create, validate, and assess TiRTC embedded Hardware IR files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from audio_contract import verify_contract as verify_audio_contract
from runtime_contract import verify_contract as verify_runtime_contract
from video_contract import verify_contract as verify_video_contract


FEATURES = {
    "h5_live_audio",
    "h5_live_video",
    "h5_talkback",
    "ai_talk",
    "device_call",
    "wechat_voip",
}
AUDIO_FEATURES = {
    "h5_live_audio",
    "h5_talkback",
    "ai_talk",
    "device_call",
    "wechat_voip",
}
AEC_REQUIRED_FEATURES = {"ai_talk", "device_call", "wechat_voip"}
BUSINESS_FEATURES = {"device_call", "wechat_voip"}
VIDEO_FEATURES = {"h5_live_video"}
VERIFICATION_LEVELS = {
    "extracted": 1,
    "corroborated": 2,
    "build_verified": 3,
    "hardware_verified": 4,
    "hil_verified": 5,
}
ASSESSMENT_PHASES = {"intake", "build", "hil"}
PHASE_SUCCESS_STATUSES = {
    "intake": {"READY_TO_PORT", "HIL_VERIFIED"},
    "build": {"BUILD_VERIFIED", "HIL_VERIFIED"},
    "hil": {"HIL_VERIFIED"},
}
VIDEO_CONTRACTS = {
    "mjpeg": "jpeg_complete_frames",
    "h264": "h264_annex_b_access_units",
    "h265": "h265_annex_b_access_units",
}
WIFI_METHOD_TYPES = {
    "softap",
    "ble",
    "smartconfig",
    "factory_nvs",
    "development_config",
    "custom",
}
SOFTAP_SSID_PREFIX = "TiRTC-"
SOFTAP_AUTH_MODE = "open"
SOFTAP_IPV4_ADDRESS = "192.168.6.1"
BINDING_METHOD_TYPES = {
    "verification_code",
    "factory_bound",
    "development_credentials",
    "custom",
}
ACCEPTANCE_LEVELS = {"L-1", "L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"}
FEATURE_HIL_LEVEL = {
    "h5_live_audio": "L5",
    "h5_live_video": "L5",
    "h5_talkback": "L5",
    "ai_talk": "L6",
    "device_call": "L6",
    "wechat_voip": "L6",
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SOURCE_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
ALLOWED_SOURCE_SCHEMES = {
    "http",
    "https",
    "device-kit",
    "managed",
    "official",
    "user-input",
    "user-supplied",
}
Requirement = tuple[str, str, int]


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_source_locations(data: dict[str, Any], ir_directory: Path) -> list[str]:
    """Resolve local evidence and reject invented or machine-bound source locators."""
    errors: list[str] = []
    root = ir_directory.expanduser().resolve()
    sources = data.get("sources")
    if not isinstance(sources, list):
        return errors
    for index, item in enumerate(sources):
        if not isinstance(item, dict):
            continue
        prefix = f"sources[{index}]"
        location = item.get("location")
        if not isinstance(location, str) or not location.strip():
            continue
        if ";" in location:
            errors.append(
                f"{prefix}.location must identify exactly one source, not a semicolon list"
            )
            continue
        scheme_match = SOURCE_SCHEME_RE.match(location)
        if scheme_match is not None:
            scheme = scheme_match.group(1).lower()
            if scheme not in ALLOWED_SOURCE_SCHEMES:
                errors.append(
                    f"{prefix}.location uses unsupported source scheme {scheme!r}"
                )
            continue
        relative = Path(location)
        if relative.is_absolute():
            errors.append(
                f"{prefix}.location must be IR-relative or a supported source URI"
            )
            continue
        resolved = (root / relative).resolve()
        if not resolved.exists():
            errors.append(
                f"{prefix}.location does not resolve from the IR directory: {location}"
            )
            continue
        expected_sha = item.get("sha256")
        if expected_sha is not None:
            if not resolved.is_file():
                errors.append(f"{prefix}.sha256 can only describe a regular file")
            elif sha256_file(resolved).lower() != str(expected_sha).lower():
                errors.append(f"{prefix}.sha256 does not match {location}")
    return errors


def mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return {}
    return value


def nonempty_string(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")


def nullable_string(value: Any, path: str, errors: list[str]) -> None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        errors.append(f"{path} must be a non-empty string or null")


def positive_int(value: Any, path: str, errors: list[str], allow_zero: bool = False) -> None:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        errors.append(f"{path} must be an integer >= {minimum}")


def nullable_positive_int(value: Any, path: str, errors: list[str]) -> None:
    if value is not None:
        positive_int(value, path, errors)


def nullable_bool(value: Any, path: str, errors: list[str]) -> None:
    if value is not None and not isinstance(value, bool):
        errors.append(f"{path} must be true, false, or null")


def validate_verification(value: Any, path: str, errors: list[str]) -> None:
    if value not in VERIFICATION_LEVELS:
        errors.append(f"{path} must be one of " + ", ".join(VERIFICATION_LEVELS))


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
        validate_verification(codec.get("verification"), f"{prefix}.verification", errors)


def validate_video_profiles(
    camera: dict[str, Any], source_ids: set[str], errors: list[str]
) -> None:
    nullable_string(
        camera.get("selected_video_profile"),
        "camera.selected_video_profile",
        errors,
    )
    profiles = camera.get("video_profiles")
    if not isinstance(profiles, list):
        errors.append("camera.video_profiles must be an array")
        return
    ids: set[str] = set()
    for index, item in enumerate(profiles):
        prefix = f"camera.video_profiles[{index}]"
        profile = mapping(item, prefix, errors)
        nonempty_string(profile.get("id"), f"{prefix}.id", errors)
        profile_id = profile.get("id")
        if isinstance(profile_id, str) and profile_id:
            if profile_id in ids:
                errors.append(f"duplicate video profile id {profile_id!r}")
            ids.add(profile_id)
        codec = profile.get("codec")
        if codec not in VIDEO_CONTRACTS:
            errors.append(
                f"{prefix}.codec must be one of " + ", ".join(VIDEO_CONTRACTS)
            )
        nullable_bool(profile.get("available"), f"{prefix}.available", errors)
        nullable_string(profile.get("output_format"), f"{prefix}.output_format", errors)
        nullable_bool(
            profile.get("refresh_frame_control"),
            f"{prefix}.refresh_frame_control",
            errors,
        )
        nullable_positive_int(profile.get("stream_id"), f"{prefix}.stream_id", errors)
        validate_verification(
            profile.get("verification"), f"{prefix}.verification", errors
        )
        validate_source_refs(profile, prefix, source_ids, errors)
    selected = camera.get("selected_video_profile")
    if isinstance(selected, str) and selected and selected not in ids:
        errors.append(
            f"camera.selected_video_profile references unknown profile {selected!r}"
        )


def validate_hardware_resources(
    data: dict[str, Any], source_ids: set[str], errors: list[str]
) -> None:
    resources = mapping(data.get("hardware_resources"), "hardware_resources", errors)
    validate_source_refs(resources, "hardware_resources", source_ids, errors)

    i2c = mapping(resources.get("i2c"), "hardware_resources.i2c", errors)
    nullable_bool(i2c.get("used"), "hardware_resources.i2c.used", errors)
    driver_family = i2c.get("driver_family")
    if driver_family not in {None, "legacy", "ng", "none"}:
        errors.append(
            "hardware_resources.i2c.driver_family must be legacy, ng, none, or null"
        )
    nullable_bool(
        i2c.get("single_driver_family"),
        "hardware_resources.i2c.single_driver_family",
        errors,
    )
    validate_verification(
        i2c.get("verification"), "hardware_resources.i2c.verification", errors
    )

    i2s = mapping(resources.get("i2s"), "hardware_resources.i2s", errors)
    nullable_bool(i2s.get("used"), "hardware_resources.i2s.used", errors)
    nullable_bool(
        i2s.get("controller_and_gpio_ownership_resolved"),
        "hardware_resources.i2s.controller_and_gpio_ownership_resolved",
        errors,
    )
    validate_verification(
        i2s.get("verification"), "hardware_resources.i2s.verification", errors
    )
    audio_contract = resources.get("audio_semantic_contract")
    nullable_string(
        audio_contract,
        "hardware_resources.audio_semantic_contract",
        errors,
    )
    if isinstance(audio_contract, str) and Path(audio_contract).is_absolute():
        errors.append(
            "hardware_resources.audio_semantic_contract must be project-relative"
        )
    video_contract = resources.get("video_semantic_contract")
    nullable_string(
        video_contract,
        "hardware_resources.video_semantic_contract",
        errors,
    )
    if isinstance(video_contract, str) and Path(video_contract).is_absolute():
        errors.append(
            "hardware_resources.video_semantic_contract must be project-relative"
        )
    runtime_contract = resources.get("runtime_semantic_contract")
    nullable_string(
        runtime_contract,
        "hardware_resources.runtime_semantic_contract",
        errors,
    )
    if isinstance(runtime_contract, str) and Path(runtime_contract).is_absolute():
        errors.append(
            "hardware_resources.runtime_semantic_contract must be project-relative"
        )

    mapping_section = mapping(
        resources.get("audio_channel_mapping"),
        "hardware_resources.audio_channel_mapping",
        errors,
    )
    nullable_bool(
        mapping_section.get("required"),
        "hardware_resources.audio_channel_mapping.required",
        errors,
    )
    nullable_bool(
        mapping_section.get("resolved"),
        "hardware_resources.audio_channel_mapping.resolved",
        errors,
    )
    validate_verification(
        mapping_section.get("verification"),
        "hardware_resources.audio_channel_mapping.verification",
        errors,
    )

    duplex = mapping(
        resources.get("duplex_audio", {}),
        "hardware_resources.duplex_audio",
        errors,
    )
    for field in (
        "simultaneous_capture_playback",
        "playback_reference_available",
        "aec_implementation_available",
    ):
        nullable_bool(
            duplex.get(field),
            f"hardware_resources.duplex_audio.{field}",
            errors,
        )
    if "verification" in duplex:
        validate_verification(
            duplex.get("verification"),
            "hardware_resources.duplex_audio.verification",
            errors,
        )

    realtime = mapping(
        resources.get("camera_realtime"),
        "hardware_resources.camera_realtime",
        errors,
    )
    nullable_bool(
        realtime.get("pipeline_safe"),
        "hardware_resources.camera_realtime.pipeline_safe",
        errors,
    )
    validate_verification(
        realtime.get("verification"),
        "hardware_resources.camera_realtime.verification",
        errors,
    )

    memory = mapping(resources.get("memory"), "hardware_resources.memory", errors)
    nullable_bool(
        memory.get("startup_and_media_budgeted"),
        "hardware_resources.memory.startup_and_media_budgeted",
        errors,
    )
    validate_verification(
        memory.get("verification"), "hardware_resources.memory.verification", errors
    )


def validate_onboarding(
    data: dict[str, Any], source_ids: set[str], errors: list[str]
) -> None:
    onboarding = mapping(data.get("onboarding"), "onboarding", errors)
    validate_source_refs(onboarding, "onboarding", source_ids, errors)
    wifi = mapping(onboarding.get("wifi_credentials"), "onboarding.wifi_credentials", errors)
    nullable_string(
        wifi.get("selected_method"), "onboarding.wifi_credentials.selected_method", errors
    )
    nullable_bool(
        wifi.get("credentials_committed_to_source"),
        "onboarding.wifi_credentials.credentials_committed_to_source",
        errors,
    )
    nullable_bool(
        wifi.get("reprovisioning_defined"),
        "onboarding.wifi_credentials.reprovisioning_defined",
        errors,
    )
    methods = wifi.get("methods")
    method_ids: set[str] = set()
    if not isinstance(methods, list):
        errors.append("onboarding.wifi_credentials.methods must be an array")
    else:
        for index, item in enumerate(methods):
            prefix = f"onboarding.wifi_credentials.methods[{index}]"
            method = mapping(item, prefix, errors)
            nonempty_string(method.get("id"), f"{prefix}.id", errors)
            method_id = method.get("id")
            if isinstance(method_id, str) and method_id:
                if method_id in method_ids:
                    errors.append(f"duplicate Wi-Fi method id {method_id!r}")
                method_ids.add(method_id)
            method_type = method.get("type")
            if method_type not in WIFI_METHOD_TYPES:
                errors.append(
                    f"{prefix}.type must be one of " + ", ".join(sorted(WIFI_METHOD_TYPES))
                )
            if method_type == "softap":
                for field in ("ssid_prefix", "auth_mode", "ipv4_address"):
                    nullable_string(method.get(field), f"{prefix}.{field}", errors)
            nullable_bool(method.get("available"), f"{prefix}.available", errors)
            validate_verification(
                method.get("verification"), f"{prefix}.verification", errors
            )
            validate_source_refs(method, prefix, source_ids, errors)
    selected = wifi.get("selected_method")
    if isinstance(selected, str) and selected and selected not in method_ids:
        errors.append(
            f"onboarding.wifi_credentials.selected_method references unknown method {selected!r}"
        )

    binding = mapping(onboarding.get("device_binding"), "onboarding.device_binding", errors)
    nullable_string(
        binding.get("selected_method"),
        "onboarding.device_binding.selected_method",
        errors,
    )
    for field in (
        "credentials_committed_to_source",
        "stored_credential_state_handled",
        "clear_binding_control",
    ):
        nullable_bool(binding.get(field), f"onboarding.device_binding.{field}", errors)
    methods = binding.get("methods")
    method_ids = set()
    if not isinstance(methods, list):
        errors.append("onboarding.device_binding.methods must be an array")
    else:
        for index, item in enumerate(methods):
            prefix = f"onboarding.device_binding.methods[{index}]"
            method = mapping(item, prefix, errors)
            nonempty_string(method.get("id"), f"{prefix}.id", errors)
            method_id = method.get("id")
            if isinstance(method_id, str) and method_id:
                if method_id in method_ids:
                    errors.append(f"duplicate binding method id {method_id!r}")
                method_ids.add(method_id)
            method_type = method.get("type")
            if method_type not in BINDING_METHOD_TYPES:
                errors.append(
                    f"{prefix}.type must be one of "
                    + ", ".join(sorted(BINDING_METHOD_TYPES))
                )
            nullable_bool(method.get("available"), f"{prefix}.available", errors)
            validate_verification(
                method.get("verification"), f"{prefix}.verification", errors
            )
            validate_source_refs(method, prefix, source_ids, errors)
    selected = binding.get("selected_method")
    if isinstance(selected, str) and selected and selected not in method_ids:
        errors.append(
            f"onboarding.device_binding.selected_method references unknown method {selected!r}"
        )


def validate_runtime_evidence(
    data: dict[str, Any], source_ids: set[str], errors: list[str]
) -> None:
    evidence = data.get("runtime_evidence")
    if not isinstance(evidence, list):
        errors.append("runtime_evidence must be an array")
        return
    for index, item in enumerate(evidence):
        prefix = f"runtime_evidence[{index}]"
        record = mapping(item, prefix, errors)
        sha = record.get("artifact_sha256")
        if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
            errors.append(f"{prefix}.artifact_sha256 must be a 64-character SHA-256")
        levels = record.get("acceptance_levels")
        if not isinstance(levels, list) or not levels:
            errors.append(f"{prefix}.acceptance_levels must be a non-empty array")
        else:
            for level_index, level in enumerate(levels):
                if level not in ACCEPTANCE_LEVELS:
                    errors.append(
                        f"{prefix}.acceptance_levels[{level_index}] must be a known acceptance level"
                    )
        features = record.get("features")
        if not isinstance(features, list) or not features:
            errors.append(f"{prefix}.features must be a non-empty array")
        else:
            for feature_index, feature in enumerate(features):
                if feature not in FEATURES:
                    errors.append(
                        f"{prefix}.features[{feature_index}] must be a known feature"
                    )
        validate_source_refs(record, prefix, source_ids, errors)


def validate_build_evidence(data: dict[str, Any], errors: list[str]) -> None:
    if "build_evidence" not in data:
        return
    evidence = mapping(data.get("build_evidence"), "build_evidence", errors)
    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("build_evidence.artifacts must be an array")
        return
    for index, item in enumerate(artifacts):
        prefix = f"build_evidence.artifacts[{index}]"
        record = mapping(item, prefix, errors)
        path_value = record.get("path")
        nonempty_string(path_value, f"{prefix}.path", errors)
        if isinstance(path_value, str) and Path(path_value).is_absolute():
            errors.append(f"{prefix}.path must be project-relative")
        positive_int(record.get("size_bytes"), f"{prefix}.size_bytes", errors)
        sha = record.get("sha256")
        if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
            errors.append(f"{prefix}.sha256 must be a 64-character SHA-256")


def validate_ir(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_version = data.get("schema_version")
    if schema_version not in {1, 2}:
        errors.append("schema_version must be 1 or 2")

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
            source_sha = source.get("sha256")
            if source_sha is not None and (
                not isinstance(source_sha, str) or not SHA256_RE.fullmatch(source_sha)
            ):
                errors.append(f"{prefix}.sha256 must be a 64-character SHA-256")
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
    validate_verification(
        toolchain.get("verification"), "toolchain.verification", errors
    )
    tirtc = mapping(toolchain.get("tirtc"), "toolchain.tirtc", errors)
    for key in ("platform", "version", "sdk_path", "build_contract"):
        nonempty_string(tirtc.get(key), f"toolchain.tirtc.{key}", errors)
    validate_source_refs(toolchain, "toolchain", source_ids, errors)

    camera = mapping(data.get("camera"), "camera", errors)
    nullable_bool(camera.get("present"), "camera.present", errors)
    if schema_version == 1:
        h264 = mapping(camera.get("h264"), "camera.h264", errors)
        nullable_bool(h264.get("available"), "camera.h264.available", errors)
        nullable_bool(
            h264.get("key_frame_control"), "camera.h264.key_frame_control", errors
        )
        validate_verification(
            h264.get("verification"), "camera.h264.verification", errors
        )
    elif schema_version == 2:
        validate_video_profiles(camera, source_ids, errors)
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

    if schema_version == 2:
        validate_hardware_resources(data, source_ids, errors)
        validate_onboarding(data, source_ids, errors)
        validate_build_evidence(data, errors)
        validate_runtime_evidence(data, source_ids, errors)
    return errors


def minimum_verification_for_phase(phase: str) -> str:
    if phase == "intake":
        return "corroborated"
    return "build_verified"


def codec_requirement(
    media: dict[str, Any], section: str, minimum_verification: str = "corroborated"
) -> Requirement:
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
        if level < VERIFICATION_LEVELS[minimum_verification]:
            return (
                "NEEDS_CONFIRMATION",
                f"{section} A-law 8 kHz path is only {verification}; "
                f"{minimum_verification} is required",
                level,
            )
        return "SATISFIED", f"{section} provides A-law 8 kHz", level
    return "BLOCKED", f"{section} has no A-law 8 kHz path", 0


def legacy_video_requirement(
    camera: dict[str, Any], minimum_verification: str = "corroborated"
) -> Requirement:
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
    if level < VERIFICATION_LEVELS[minimum_verification]:
        return (
            "NEEDS_CONFIRMATION",
            f"H.264 Annex-B path is only {verification}; "
            f"{minimum_verification} is required",
            level,
        )
    return "SATISFIED", "camera provides H.264 Annex-B and IDR control", level


def selected_item(items: Any, selected_id: Any) -> dict[str, Any] | None:
    if not isinstance(items, list) or not isinstance(selected_id, str):
        return None
    for item in items:
        if isinstance(item, dict) and item.get("id") == selected_id:
            return item
    return None


def video_requirement_v2(
    camera: dict[str, Any], minimum_verification: str = "corroborated"
) -> Requirement:
    present = camera.get("present")
    if present is None:
        return "NEEDS_CONFIRMATION", "camera presence is unknown", 0
    if present is False:
        return "BLOCKED", "camera is not present", 0
    selected_id = camera.get("selected_video_profile")
    if not isinstance(selected_id, str) or not selected_id:
        return "NEEDS_CONFIRMATION", "selected video profile is unknown", 0
    profile = selected_item(camera.get("video_profiles"), selected_id)
    if profile is None:
        return "BLOCKED", f"selected video profile {selected_id!r} does not exist", 0
    codec = profile.get("codec")
    if codec not in VIDEO_CONTRACTS:
        return "BLOCKED", f"selected video codec {codec!r} is unsupported", 0
    available = profile.get("available")
    if available is None:
        return "NEEDS_CONFIRMATION", f"{codec} path availability is unknown", 0
    if available is False:
        return "BLOCKED", f"selected {codec} path is unavailable", 0
    output_format = profile.get("output_format")
    if output_format is None:
        return "NEEDS_CONFIRMATION", f"{codec} output format is unknown", 0
    expected = VIDEO_CONTRACTS[codec]
    if str(output_format).lower() != expected:
        return (
            "BLOCKED",
            f"selected {codec} profile requires output_format={expected}",
            0,
        )
    refresh = profile.get("refresh_frame_control")
    if refresh is None:
        return "NEEDS_CONFIRMATION", "refresh/key-frame control is unknown", 0
    if refresh is False:
        return "BLOCKED", "H5 refresh requests cannot reach the media pipeline", 0
    verification = profile.get("verification")
    level = VERIFICATION_LEVELS.get(verification, 0)
    if level < VERIFICATION_LEVELS[minimum_verification]:
        return (
            "NEEDS_CONFIRMATION",
            f"selected {codec} path is only {verification}; "
            f"{minimum_verification} is required",
            level,
        )
    return (
        "SATISFIED",
        f"selected {codec} profile provides {expected} on stream {profile.get('stream_id')}",
        level,
    )


def verified_bool_requirement(
    section: dict[str, Any],
    field: str,
    label: str,
    minimum_verification: str = "corroborated",
) -> Requirement:
    value = section.get(field)
    if value is None:
        return "NEEDS_CONFIRMATION", f"{label} is unknown", 0
    if value is False:
        return "BLOCKED", f"{label} is unresolved", 0
    verification = section.get("verification")
    level = VERIFICATION_LEVELS.get(verification, 0)
    if level < VERIFICATION_LEVELS[minimum_verification]:
        return (
            "NEEDS_CONFIRMATION",
            f"{label} is only {verification}; {minimum_verification} is required",
            level,
        )
    return "SATISFIED", f"{label} is resolved", level


def i2c_requirement(
    resources: dict[str, Any], minimum_verification: str = "corroborated"
) -> Requirement:
    i2c = resources.get("i2c", {})
    used = i2c.get("used")
    if used is None:
        return "NEEDS_CONFIRMATION", "I2C usage is unknown", 0
    if used is False:
        return "SATISFIED", "board media path does not use I2C", 2
    family = i2c.get("driver_family")
    if family is None:
        return "NEEDS_CONFIRMATION", "I2C driver family is unknown", 0
    if family == "none":
        return "BLOCKED", "I2C is used but no driver family is selected", 0
    return verified_bool_requirement(
        i2c,
        "single_driver_family",
        f"single {family} I2C driver family plan",
        minimum_verification,
    )


def i2s_requirement(
    resources: dict[str, Any], minimum_verification: str = "corroborated"
) -> Requirement:
    i2s = resources.get("i2s", {})
    used = i2s.get("used")
    if used is None:
        return "NEEDS_CONFIRMATION", "I2S usage is unknown", 0
    if used is False:
        return "SATISFIED", "audio path does not use I2S", 2
    return verified_bool_requirement(
        i2s,
        "controller_and_gpio_ownership_resolved",
        "I2S controller and GPIO ownership plan",
        minimum_verification,
    )


def audio_mapping_requirement(
    resources: dict[str, Any], minimum_verification: str = "corroborated"
) -> Requirement:
    channel = resources.get("audio_channel_mapping", {})
    required = channel.get("required")
    if required is None:
        return "NEEDS_CONFIRMATION", "audio channel/TDM mapping requirement is unknown", 0
    if required is False:
        return "SATISFIED", "audio channel/TDM mapping is not required", 2
    return verified_bool_requirement(
        channel,
        "resolved",
        "audio channel/TDM mapping",
        minimum_verification,
    )


def aec_capability_requirement(
    resources: dict[str, Any], minimum_verification: str = "corroborated"
) -> Requirement:
    duplex = resources.get("duplex_audio", {})
    for field, label in (
        ("simultaneous_capture_playback", "simultaneous capture and playback"),
        ("playback_reference_available", "physical playback-reference capture path"),
        ("aec_implementation_available", "AEC processor implementation"),
    ):
        requirement = verified_bool_requirement(
            duplex, field, label, minimum_verification
        )
        if requirement[0] != "SATISFIED":
            return requirement
    return (
        "SATISFIED",
        "full-duplex audio, playback reference, and AEC implementation are resolved",
        VERIFICATION_LEVELS.get(duplex.get("verification"), 0),
    )


def camera_realtime_requirement(
    resources: dict[str, Any], minimum_verification: str = "corroborated"
) -> Requirement:
    return verified_bool_requirement(
        resources.get("camera_realtime", {}),
        "pipeline_safe",
        "camera DMA/task realtime policy design",
        minimum_verification,
    )


def memory_requirement(
    resources: dict[str, Any], minimum_verification: str = "corroborated"
) -> Requirement:
    return verified_bool_requirement(
        resources.get("memory", {}),
        "startup_and_media_budgeted",
        "static startup and media memory budget",
        minimum_verification,
    )


def wifi_requirement(onboarding: dict[str, Any]) -> Requirement:
    wifi = onboarding.get("wifi_credentials", {})
    committed = wifi.get("credentials_committed_to_source")
    if committed is None:
        return "NEEDS_CONFIRMATION", "credential source-control policy is unknown", 0
    if committed is True:
        return "BLOCKED", "Wi-Fi credentials are committed to source", 0
    reprovisioning = wifi.get("reprovisioning_defined")
    if reprovisioning is None:
        return "NEEDS_CONFIRMATION", "Wi-Fi reprovisioning path is unknown", 0
    if reprovisioning is False:
        return "BLOCKED", "Wi-Fi reprovisioning path is undefined", 0
    selected_id = wifi.get("selected_method")
    if not isinstance(selected_id, str) or not selected_id:
        return "NEEDS_CONFIRMATION", "Wi-Fi credential method is not selected", 0
    method = selected_item(wifi.get("methods"), selected_id)
    if method is None:
        return "BLOCKED", f"selected Wi-Fi method {selected_id!r} does not exist", 0
    available = method.get("available")
    if available is None:
        return "NEEDS_CONFIRMATION", "selected Wi-Fi method availability is unknown", 0
    if available is False:
        return "BLOCKED", "selected Wi-Fi method is unavailable", 0
    if method.get("type") == "softap":
        softap_fields = (
            ("ssid_prefix", SOFTAP_SSID_PREFIX, "SSID prefix"),
            ("auth_mode", SOFTAP_AUTH_MODE, "authentication mode"),
            ("ipv4_address", SOFTAP_IPV4_ADDRESS, "IPv4 address"),
        )
        for field, expected, label in softap_fields:
            value = method.get(field)
            if value is None:
                return (
                    "NEEDS_CONFIRMATION",
                    f"SoftAP {label} is unknown; expected {expected!r}",
                    0,
                )
            if value != expected:
                return (
                    "BLOCKED",
                    f"SoftAP {label} must be {expected!r}, got {value!r}",
                    0,
                )
    verification = method.get("verification")
    level = VERIFICATION_LEVELS.get(verification, 0)
    if level < VERIFICATION_LEVELS["corroborated"]:
        return (
            "NEEDS_CONFIRMATION",
            f"selected Wi-Fi method is only {verification}",
            level,
        )
    return (
        "SATISFIED",
        f"Wi-Fi credentials use {method.get('type')} outside source control",
        level,
    )


def binding_requirement(onboarding: dict[str, Any]) -> Requirement:
    binding = onboarding.get("device_binding", {})
    committed = binding.get("credentials_committed_to_source")
    if committed is None:
        return "NEEDS_CONFIRMATION", "device credential source-control policy is unknown", 0
    if committed is True:
        return "BLOCKED", "device credentials are committed to source", 0
    for field in ("stored_credential_state_handled", "clear_binding_control"):
        value = binding.get(field)
        if value is None:
            return "NEEDS_CONFIRMATION", f"device binding {field} is unknown", 0
        if value is False:
            return "BLOCKED", f"device binding {field} is unsupported", 0
    selected_id = binding.get("selected_method")
    if not isinstance(selected_id, str) or not selected_id:
        return "NEEDS_CONFIRMATION", "device binding method is not selected", 0
    method = selected_item(binding.get("methods"), selected_id)
    if method is None:
        return "BLOCKED", f"selected binding method {selected_id!r} does not exist", 0
    available = method.get("available")
    if available is None:
        return "NEEDS_CONFIRMATION", "selected binding method availability is unknown", 0
    if available is False:
        return "BLOCKED", "selected binding method is unavailable", 0
    verification = method.get("verification")
    level = VERIFICATION_LEVELS.get(verification, 0)
    if level < VERIFICATION_LEVELS["corroborated"]:
        return (
            "NEEDS_CONFIRMATION",
            f"selected binding method is only {verification}",
            level,
        )
    return (
        "SATISFIED",
        f"device binding uses {method.get('type')} outside source control",
        level,
    )


def combine_requirements(
    requirements: list[Requirement],
    success_status: str = "READY_TO_PORT",
    legacy_hil_from_levels: bool = False,
) -> dict[str, Any]:
    reasons = [reason for _, reason, _ in requirements]
    states = {state for state, _, _ in requirements}
    levels = [level for state, _, level in requirements if state == "SATISFIED"]
    if "BLOCKED" in states:
        status = "BLOCKED"
    elif "NEEDS_CONFIRMATION" in states:
        status = "NEEDS_CONFIRMATION"
    elif (
        legacy_hil_from_levels
        and levels
        and min(levels) >= VERIFICATION_LEVELS["hil_verified"]
    ):
        status = "HIL_VERIFIED"
    else:
        status = success_status
    return {"status": status, "reasons": reasons}


def constrain_project_gate(
    project_gate: dict[str, Any], feature_assessments: dict[str, dict[str, Any]]
) -> None:
    """Prevent a project-level pass while a requested feature is unresolved."""
    feature_states = {item["status"] for item in feature_assessments.values()}
    if "BLOCKED" in feature_states:
        project_gate["status"] = "BLOCKED"
        project_gate["reasons"].append("at least one requested feature is blocked")
    elif (
        "NEEDS_CONFIRMATION" in feature_states
        and project_gate["status"] != "BLOCKED"
    ):
        project_gate["status"] = "NEEDS_CONFIRMATION"
        project_gate["reasons"].append(
            "at least one requested feature still needs confirmation"
        )


def project_requirements(data: dict[str, Any]) -> list[Requirement]:
    requirements: list[Requirement] = []
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
    if target not in {"esp32s3", "esp32p4"}:
        requirements.append(
            (
                "BLOCKED",
                f"TiRTC ESP32 workflow supports esp32s3 or esp32p4, not {target}",
                0,
            )
        )
    else:
        requirements.append(
            ("SATISFIED", f"{target} is a supported TiRTC target", 2)
        )

    platform = data["toolchain"]["tirtc"]["platform"].strip().lower()
    expected_platform = f"espressif-{target}"
    if target in {"esp32s3", "esp32p4"} and platform != expected_platform:
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


def matching_runtime_evidence(
    data: dict[str, Any], artifact_sha256: str | None
) -> dict[str, Any] | None:
    if artifact_sha256 is None:
        return None
    normalized = artifact_sha256.lower()
    for record in data.get("runtime_evidence", []):
        if (
            isinstance(record, dict)
            and str(record.get("artifact_sha256", "")).lower() == normalized
        ):
            return record
    return None


def matching_build_artifact(
    data: dict[str, Any], artifact_sha256: str | None
) -> dict[str, Any] | None:
    if artifact_sha256 is None:
        return None
    normalized = artifact_sha256.lower()
    build_evidence = data.get("build_evidence", {})
    if not isinstance(build_evidence, dict):
        return None
    artifacts = build_evidence.get("artifacts", [])
    if not isinstance(artifacts, list):
        return None
    for record in artifacts:
        if (
            isinstance(record, dict)
            and str(record.get("sha256", "")).lower() == normalized
        ):
            return record
    return None


def artifact_requirement(
    data: dict[str, Any], artifact_sha256: str | None
) -> Requirement:
    if artifact_sha256 is None:
        return "NEEDS_CONFIRMATION", "exact build artifact SHA-256 is missing", 0
    if not SHA256_RE.fullmatch(artifact_sha256):
        return "BLOCKED", "build artifact SHA-256 is invalid", 0
    if matching_build_artifact(data, artifact_sha256) is None:
        return (
            "BLOCKED",
            f"artifact {artifact_sha256} is not present in build_evidence.artifacts",
            0,
        )
    return (
        "SATISFIED",
        f"build evidence is bound to artifact {artifact_sha256}",
        VERIFICATION_LEVELS["build_verified"],
    )


def artifact_file_requirement(
    data: dict[str, Any], artifact_sha256: str | None, project: Path
) -> Requirement:
    recorded = artifact_requirement(data, artifact_sha256)
    if recorded[0] != "SATISFIED" or artifact_sha256 is None:
        return recorded
    record = matching_build_artifact(data, artifact_sha256)
    if record is None:
        return "BLOCKED", "matching build artifact record disappeared", 0
    value = record.get("path")
    if not isinstance(value, str) or not value:
        return "BLOCKED", "matching build artifact path is missing", 0
    relative = Path(value)
    if relative.is_absolute():
        return "BLOCKED", "matching build artifact path is not project-relative", 0
    root = project.expanduser().resolve()
    path = (root / relative).resolve()
    if root != path and root not in path.parents:
        return "BLOCKED", "matching build artifact path escapes project root", 0
    if not path.is_file():
        return "BLOCKED", f"recorded build artifact does not exist: {value}", 0
    if path.stat().st_size != record.get("size_bytes"):
        return "BLOCKED", f"recorded build artifact size is stale for {value}", 0
    if sha256_file(path).lower() != artifact_sha256.lower():
        return "BLOCKED", f"recorded build artifact SHA-256 is stale for {value}", 0
    return (
        "SATISFIED",
        f"artifact file {value} matches size and SHA-256",
        VERIFICATION_LEVELS["build_verified"],
    )


def assess_ir(
    data: dict[str, Any],
    artifact_sha256: str | None = None,
    phase: str | None = None,
    audio_gate: Requirement | None = None,
    aec_gate: Requirement | None = None,
    business_gate: Requirement | None = None,
    video_gate: Requirement | None = None,
    runtime_gate: Requirement | None = None,
    artifact_gate: Requirement | None = None,
) -> dict[str, Any]:
    selected_phase = phase or ("hil" if artifact_sha256 else "intake")
    if selected_phase not in ASSESSMENT_PHASES:
        raise ValueError(
            f"assessment phase must be one of {', '.join(sorted(ASSESSMENT_PHASES))}"
        )
    minimum_verification = minimum_verification_for_phase(selected_phase)
    success_status = (
        "READY_TO_PORT" if selected_phase == "intake" else "BUILD_VERIFIED"
    )
    schema_version = data.get("schema_version")
    requested = data["features"]["requested"]
    audio_input = data["audio_input"]
    audio_output = data["audio_output"]
    camera = data["camera"]
    result: dict[str, Any] = {}
    project = project_requirements(data)
    selected_video: dict[str, Any] | None = None
    selected_wifi: dict[str, Any] | None = None
    selected_binding: dict[str, Any] | None = None

    if schema_version == 2:
        resources = data["hardware_resources"]
        onboarding = data["onboarding"]
        project.extend(
            [
                i2c_requirement(resources, minimum_verification),
                wifi_requirement(onboarding),
                binding_requirement(onboarding),
            ]
        )
        selected_video = selected_item(
            camera.get("video_profiles"), camera.get("selected_video_profile")
        )
        wifi = onboarding.get("wifi_credentials", {})
        selected_wifi = selected_item(wifi.get("methods"), wifi.get("selected_method"))
        binding = onboarding.get("device_binding", {})
        selected_binding = selected_item(
            binding.get("methods"), binding.get("selected_method")
        )
    else:
        resources = {}

    if selected_phase in {"build", "hil"}:
        project.append(artifact_gate or artifact_requirement(data, artifact_sha256))

    for feature in requested:
        if schema_version == 1:
            if feature == "h5_live_audio":
                requirements = [
                    codec_requirement(
                        audio_input, "audio_input", minimum_verification
                    )
                ]
            elif feature == "h5_live_video":
                requirements = [
                    legacy_video_requirement(camera, minimum_verification)
                ]
            elif feature == "h5_talkback":
                requirements = [
                    codec_requirement(
                        audio_output, "audio_output", minimum_verification
                    )
                ]
            else:
                requirements = [
                    codec_requirement(
                        audio_input, "audio_input", minimum_verification
                    ),
                    codec_requirement(
                        audio_output, "audio_output", minimum_verification
                    ),
                ]
            if feature in AEC_REQUIRED_FEATURES:
                requirements.append(
                    (
                        "NEEDS_CONFIRMATION",
                        "AEC-required sessions need Hardware IR v2 duplex_audio evidence",
                        0,
                    )
                )
            result[feature] = combine_requirements(
                requirements,
                success_status=success_status,
                legacy_hil_from_levels=(selected_phase == "intake"),
            )
            continue

        if feature == "h5_live_audio":
            requirements = [
                codec_requirement(audio_input, "audio_input", minimum_verification),
                i2s_requirement(resources, minimum_verification),
                audio_mapping_requirement(resources, minimum_verification),
                memory_requirement(resources, minimum_verification),
            ]
        elif feature == "h5_live_video":
            requirements = [
                video_requirement_v2(camera, minimum_verification),
                camera_realtime_requirement(resources, minimum_verification),
                memory_requirement(resources, minimum_verification),
            ]
        elif feature == "h5_talkback":
            requirements = [
                codec_requirement(audio_output, "audio_output", minimum_verification),
                i2s_requirement(resources, minimum_verification),
                memory_requirement(resources, minimum_verification),
            ]
        else:
            requirements = [
                codec_requirement(audio_input, "audio_input", minimum_verification),
                codec_requirement(audio_output, "audio_output", minimum_verification),
                i2s_requirement(resources, minimum_verification),
                audio_mapping_requirement(resources, minimum_verification),
                memory_requirement(resources, minimum_verification),
            ]
        if feature in AEC_REQUIRED_FEATURES:
            requirements.append(
                aec_capability_requirement(resources, minimum_verification)
            )
        if feature in AUDIO_FEATURES and selected_phase in {"build", "hil"}:
            requirements.append(
                audio_gate
                or (
                    "NEEDS_CONFIRMATION",
                    "audio semantic gate was not executed for this project",
                    0,
                )
            )
        if feature in AEC_REQUIRED_FEATURES and selected_phase in {"build", "hil"}:
            requirements.append(
                aec_gate
                or (
                    "BLOCKED",
                    "AEC semantic gate did not prove simultaneous full-duplex audio and enabled echo cancellation",
                    0,
                )
            )
        if feature in VIDEO_FEATURES and selected_phase in {"build", "hil"}:
            requirements.append(
                video_gate
                or (
                    "NEEDS_CONFIRMATION",
                    "video semantic gate was not executed for this project",
                    0,
                )
            )
        if selected_phase in {"build", "hil"}:
            requirements.append(
                runtime_gate
                or (
                    "NEEDS_CONFIRMATION",
                    "TiRTC runtime semantic gate was not executed for this project",
                    0,
                )
            )
        if feature in BUSINESS_FEATURES and selected_phase in {"build", "hil"}:
            requirements.append(
                business_gate
                or (
                    "BLOCKED",
                    "business runtime gate did not prove the requested call/VoIP protocol and session arbiter",
                    0,
                )
            )
        result[feature] = combine_requirements(
            requirements, success_status=success_status
        )

    project_gate = combine_requirements(
        project,
        success_status=success_status,
        legacy_hil_from_levels=(schema_version == 1 and selected_phase == "intake"),
    )
    build_artifact = matching_build_artifact(data, artifact_sha256)
    evidence = matching_runtime_evidence(data, artifact_sha256)
    if schema_version == 2 and selected_phase == "hil":
        evidence_features = set(evidence.get("features", [])) if evidence else set()
        evidence_levels = (
            set(evidence.get("acceptance_levels", [])) if evidence else set()
        )
        for feature, feature_assessment in result.items():
            if feature_assessment["status"] != "BUILD_VERIFIED":
                continue
            required_level = FEATURE_HIL_LEVEL[feature]
            if feature in evidence_features and required_level in evidence_levels:
                feature_assessment["status"] = "HIL_VERIFIED"
                feature_assessment["reasons"].append(
                    f"artifact {artifact_sha256} passed {required_level}"
                )
            else:
                feature_assessment["reasons"].append(
                    f"artifact {artifact_sha256} has no matching {required_level} runtime evidence"
                )
        if result and all(
            item["status"] == "HIL_VERIFIED" for item in result.values()
        ) and project_gate["status"] == "BUILD_VERIFIED":
            project_gate["status"] = "HIL_VERIFIED"
            project_gate["reasons"].append(
                f"all requested features have matching artifact evidence for {artifact_sha256}"
            )

    constrain_project_gate(project_gate, result)

    assessment: dict[str, Any] = {
        "schema_version": schema_version,
        "phase": selected_phase,
        "board_id": data["board"]["id"],
        "hardware_revision": data["board"]["hardware_revision"],
        "project_gate": project_gate,
        "features": result,
    }
    if schema_version == 2:
        assessment["selected_video_profile"] = selected_video
        assessment["selected_wifi_method"] = selected_wifi
        assessment["selected_binding_method"] = selected_binding
        assessment["artifact_sha256"] = artifact_sha256
        assessment["build_artifact_evidence_matched"] = build_artifact is not None
        assessment["runtime_artifact_evidence_matched"] = evidence is not None
    return assessment


def command_init(args: argparse.Namespace) -> int:
    output = args.output.resolve()
    if output.exists():
        print(f"refusing to overwrite existing file: {output}", file=sys.stderr)
        return 2
    example = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "hardware-ir-v2.example.json"
    )
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
    errors = validate_ir(data) + validate_source_locations(data, args.path.parent)
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
    errors = validate_ir(data) + validate_source_locations(data, args.path.parent)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    if args.artifact_sha256 is not None and not SHA256_RE.fullmatch(
        args.artifact_sha256
    ):
        print("error: --artifact-sha256 must be a 64-character SHA-256", file=sys.stderr)
        return 2
    selected_phase = args.phase or (
        "hil" if args.artifact_sha256 is not None else "intake"
    )
    project = (args.project or args.path.parent).expanduser().resolve()
    audio_gate: Requirement | None = None
    aec_gate: Requirement | None = None
    audio_gate_result: dict[str, Any] | None = None
    if (
        data.get("schema_version") == 2
        and selected_phase in {"build", "hil"}
        and AUDIO_FEATURES.intersection(data["features"]["requested"])
    ):
        relative_contract = data["hardware_resources"].get(
            "audio_semantic_contract"
        )
        if not isinstance(relative_contract, str) or not relative_contract:
            audio_gate = (
                "NEEDS_CONFIRMATION",
                "hardware_resources.audio_semantic_contract is missing",
                0,
            )
            audio_gate_result = {
                "ok": False,
                "errors": ["audio semantic contract is missing"],
            }
        else:
            contract = (project / relative_contract).resolve()
            if project != contract and project not in contract.parents:
                audio_gate_result = {
                    "ok": False,
                    "errors": ["audio semantic contract escapes project root"],
                }
            else:
                audio_gate_result = verify_audio_contract(contract, project)
            if audio_gate_result["ok"]:
                audio_gate = (
                    "SATISFIED",
                    "audio semantic gate passed: "
                    + str(audio_gate_result.get("summary", "verified")),
                    VERIFICATION_LEVELS["build_verified"],
                )
                if AEC_REQUIRED_FEATURES.intersection(
                    data["features"]["requested"]
                ):
                    if (
                        audio_gate_result.get("simultaneous_capture_playback") is True
                        and audio_gate_result.get("echo_cancellation_enabled") is True
                    ):
                        aec_gate = (
                            "SATISFIED",
                            "AEC gate proved simultaneous capture/playback with echo cancellation enabled",
                            VERIFICATION_LEVELS["build_verified"],
                        )
                    else:
                        aec_gate = (
                            "BLOCKED",
                            "AI/call/VoIP requires simultaneous capture/playback and echo_cancellation.enabled=true",
                            0,
                        )
            else:
                audio_gate = (
                    "BLOCKED",
                    "audio semantic gate failed: "
                    + "; ".join(audio_gate_result.get("errors", [])),
                    0,
                )
    video_gate: Requirement | None = None
    video_gate_result: dict[str, Any] | None = None
    if (
        data.get("schema_version") == 2
        and selected_phase in {"build", "hil"}
        and VIDEO_FEATURES.intersection(data["features"]["requested"])
    ):
        relative_contract = data["hardware_resources"].get(
            "video_semantic_contract"
        )
        if not isinstance(relative_contract, str) or not relative_contract:
            video_gate = (
                "NEEDS_CONFIRMATION",
                "hardware_resources.video_semantic_contract is missing",
                0,
            )
            video_gate_result = {
                "ok": False,
                "errors": ["video semantic contract is missing"],
            }
        else:
            contract = (project / relative_contract).resolve()
            if project != contract and project not in contract.parents:
                video_gate_result = {
                    "ok": False,
                    "errors": ["video semantic contract escapes project root"],
                }
            else:
                video_gate_result = verify_video_contract(contract, project)
            if video_gate_result["ok"]:
                video_gate = (
                    "SATISFIED",
                    "video semantic gate passed: "
                    + str(video_gate_result.get("summary", "verified")),
                    VERIFICATION_LEVELS["build_verified"],
                )
            else:
                video_gate = (
                    "BLOCKED",
                    "video semantic gate failed: "
                    + "; ".join(video_gate_result.get("errors", [])),
                    0,
                )
    runtime_gate: Requirement | None = None
    business_gate: Requirement | None = None
    runtime_gate_result: dict[str, Any] | None = None
    if data.get("schema_version") == 2 and selected_phase in {"build", "hil"}:
        relative_contract = data["hardware_resources"].get(
            "runtime_semantic_contract"
        )
        if not isinstance(relative_contract, str) or not relative_contract:
            runtime_gate = (
                "NEEDS_CONFIRMATION",
                "hardware_resources.runtime_semantic_contract is missing",
                0,
            )
            runtime_gate_result = {
                "ok": False,
                "errors": ["TiRTC runtime semantic contract is missing"],
            }
        else:
            contract = (project / relative_contract).resolve()
            if project != contract and project not in contract.parents:
                runtime_gate_result = {
                    "ok": False,
                    "errors": ["TiRTC runtime semantic contract escapes project root"],
                }
            else:
                runtime_gate_result = verify_runtime_contract(contract, project)
            if runtime_gate_result.get("base_ok", runtime_gate_result["ok"]):
                requested_business = (
                    set(data["features"]["requested"]) & BUSINESS_FEATURES
                )
                verified_business = set(
                    runtime_gate_result.get("business_features", [])
                )
                missing_business = requested_business - verified_business
                runtime_gate = (
                    "SATISFIED",
                    "TiRTC base runtime semantic gate passed: "
                    + str(runtime_gate_result.get("summary", "verified")),
                    VERIFICATION_LEVELS["build_verified"],
                )
                if requested_business and (
                    runtime_gate_result.get("business_ok") is not True
                    or missing_business
                ):
                    details = list(runtime_gate_result.get("business_errors", []))
                    if missing_business:
                        details.append(
                            "missing features: " + ", ".join(sorted(missing_business))
                        )
                    business_gate = (
                        "BLOCKED",
                        "TiRTC business runtime gate failed: " + "; ".join(details),
                        0,
                    )
                elif requested_business:
                    business_gate = (
                        "SATISFIED",
                        "TiRTC business runtime gate verified: "
                        + ", ".join(sorted(requested_business)),
                        VERIFICATION_LEVELS["build_verified"],
                    )
            else:
                runtime_gate = (
                    "BLOCKED",
                    "TiRTC runtime semantic gate failed: "
                    + "; ".join(runtime_gate_result.get("errors", [])),
                    0,
                )
    artifact_gate = (
        artifact_file_requirement(data, args.artifact_sha256, project)
        if selected_phase in {"build", "hil"}
        else None
    )
    try:
        assessment = assess_ir(
            data,
            artifact_sha256=args.artifact_sha256,
            phase=selected_phase,
            audio_gate=audio_gate,
            aec_gate=aec_gate,
            business_gate=business_gate,
            video_gate=video_gate,
            runtime_gate=runtime_gate,
            artifact_gate=artifact_gate,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if audio_gate_result is not None:
        assessment["audio_semantic_gate"] = audio_gate_result
    if video_gate_result is not None:
        assessment["video_semantic_gate"] = video_gate_result
    if runtime_gate_result is not None:
        assessment["runtime_semantic_gate"] = runtime_gate_result
    print(json.dumps(assessment, ensure_ascii=False, indent=2))
    if args.strict:
        statuses = {item["status"] for item in assessment["features"].values()}
        statuses.add(assessment["project_gate"]["status"])
        allowed_statuses = PHASE_SUCCESS_STATUSES[assessment["phase"]]
        if not statuses.issubset(allowed_statuses):
            return 3
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create, validate, and assess TiRTC embedded Hardware IR files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a new Hardware IR v2")
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
        help="return non-zero unless every requested feature passes the selected phase",
    )
    assess_parser.add_argument(
        "--phase",
        choices=sorted(ASSESSMENT_PHASES),
        help="assessment phase; defaults to intake, or hil when an artifact SHA is supplied",
    )
    assess_parser.add_argument(
        "--artifact-sha256",
        help="bind build or HIL assessment to this exact firmware artifact",
    )
    assess_parser.add_argument(
        "--project",
        type=Path,
        help="generated project root; defaults to the Hardware IR directory",
    )
    assess_parser.set_defaults(handler=command_assess)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

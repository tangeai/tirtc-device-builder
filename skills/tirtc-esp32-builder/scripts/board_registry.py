#!/usr/bin/env python3
"""Validate and query reusable ESP32 board knowledge without guessing identity."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from hardware_ir import load_ir, validate_ir, validate_source_locations


SCHEMA_VERSION = 1
PACKAGE_STATUSES = {"knowledge_only", "adapter_verified", "hil_verified"}
LESSON_SCOPES = {"generic", "component", "board"}
LESSON_VERIFICATION = {
    "reported",
    "corroborated",
    "build_verified",
    "hardware_verified",
    "hil_verified",
}
ACTION_KINDS = {"prefer", "require", "warn", "block_until_hil"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid {label} JSON at line {exc.lineno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value


def normalized(value: Any) -> str:
    return str(value).strip().casefold() if value is not None else ""


def nonempty(value: Any, path: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")
        return False
    return True


def nullable_nonempty(value: Any, path: str, errors: list[str]) -> None:
    if value is not None:
        nonempty(value, path, errors)


def nullable_positive_int(value: Any, path: str, errors: list[str]) -> None:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
    ):
        errors.append(f"{path} must be a positive integer or null")


def string_array(value: Any, path: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if nonempty(item, f"{path}[{index}]", errors):
            result.append(item)
    return result


def validate_component(item: Any, path: str, errors: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f"{path} must be an object")
        return
    nonempty(item.get("kind"), f"{path}.kind", errors)
    nonempty(item.get("model"), f"{path}.model", errors)


def validate_probe(item: Any, path: str, errors: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f"{path} must be an object")
        return
    nonempty(item.get("kind"), f"{path}.kind", errors)
    nonempty(item.get("value"), f"{path}.value", errors)
    required = item.get("required_for_exact")
    if not isinstance(required, bool):
        errors.append(f"{path}.required_for_exact must be true or false")


def validate_identity(identity: Any, path: str, errors: list[str]) -> None:
    if not isinstance(identity, dict):
        errors.append(f"{path} must be an object")
        return
    for field in ("vendor", "model", "hardware_revision", "target"):
        nonempty(identity.get(field), f"{path}.{field}", errors)
    aliases = string_array(identity.get("aliases", []), f"{path}.aliases", errors)
    names = [identity.get("model"), *aliases]
    normalized_names = [normalized(value) for value in names if normalized(value)]
    if len(normalized_names) != len(set(normalized_names)):
        errors.append(f"{path}.model and aliases must be unique")
    nullable_nonempty(identity.get("module"), f"{path}.module", errors)
    nullable_positive_int(identity.get("flash_mb"), f"{path}.flash_mb", errors)
    nullable_positive_int(identity.get("psram_mb"), f"{path}.psram_mb", errors)
    components = identity.get("components", [])
    if not isinstance(components, list):
        errors.append(f"{path}.components must be an array")
    else:
        for index, item in enumerate(components):
            validate_component(item, f"{path}.components[{index}]", errors)
    probes = identity.get("probes", [])
    if not isinstance(probes, list):
        errors.append(f"{path}.probes must be an array")
    else:
        for index, item in enumerate(probes):
            validate_probe(item, f"{path}.probes[{index}]", errors)


def safe_registry_path(registry_path: Path, value: Any, path: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty registry-relative path")
        return None
    relative = Path(value)
    if relative.is_absolute():
        errors.append(f"{path} must be registry-relative")
        return None
    root = registry_path.parent.resolve()
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        errors.append(f"{path} escapes the registry root")
        return None
    return resolved


def validate_lesson(
    lesson: Any,
    path: str,
    package_id: str,
    board_ids: set[str],
    registry_path: Path,
    errors: list[str],
) -> None:
    if not isinstance(lesson, dict):
        errors.append(f"{path} must be an object")
        return
    nonempty(lesson.get("id"), f"{path}.id", errors)
    scope = lesson.get("scope")
    if scope not in LESSON_SCOPES:
        errors.append(f"{path}.scope must be one of {', '.join(sorted(LESSON_SCOPES))}")
    nonempty(lesson.get("subject"), f"{path}.subject", errors)
    nonempty(lesson.get("guidance"), f"{path}.guidance", errors)
    action = lesson.get("action")
    if action not in ACTION_KINDS:
        errors.append(f"{path}.action must be one of {', '.join(sorted(ACTION_KINDS))}")
    verification = lesson.get("verification")
    if verification not in LESSON_VERIFICATION:
        errors.append(
            f"{path}.verification must be one of "
            + ", ".join(sorted(LESSON_VERIFICATION))
        )
    applies_to = lesson.get("applies_to")
    if not isinstance(applies_to, dict):
        errors.append(f"{path}.applies_to must be an object")
        applies_to = {}
    if scope == "board" and applies_to.get("package_id") != package_id:
        errors.append(f"{path} board lesson must target its containing package")
    if scope == "component":
        nonempty(applies_to.get("kind"), f"{path}.applies_to.kind", errors)
        nonempty(applies_to.get("model"), f"{path}.applies_to.model", errors)

    evidence = lesson.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{path}.evidence must be a non-empty array")
        evidence = []
    evidence_boards: set[str] = set()
    for index, item in enumerate(evidence):
        prefix = f"{path}.evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        board_id = item.get("board_package_id")
        if nonempty(board_id, f"{prefix}.board_package_id", errors):
            evidence_boards.add(board_id)
            if board_id not in board_ids:
                errors.append(f"{prefix}.board_package_id is not registered")
        nullable_nonempty(item.get("source_ref"), f"{prefix}.source_ref", errors)
        sha = item.get("artifact_sha256")
        if sha is not None and (not isinstance(sha, str) or SHA256_RE.fullmatch(sha) is None):
            errors.append(f"{prefix}.artifact_sha256 must be a full SHA-256")

    if verification in {"hardware_verified", "hil_verified"} and not any(
        isinstance(item, dict) and item.get("artifact_sha256")
        for item in evidence
    ):
        errors.append(f"{path} hardware/HIL lesson requires artifact SHA-256 evidence")
    if scope == "generic":
        if len(evidence_boards) < 2:
            errors.append(f"{path} generic lesson requires two independent board packages")
        regression_test = safe_registry_path(
            registry_path,
            lesson.get("regression_test"),
            f"{path}.regression_test",
            errors,
        )
        if regression_test is not None and not regression_test.is_file():
            errors.append(f"{path}.regression_test does not exist")


def validate_registry(data: dict[str, Any], registry_path: Path) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    boards = data.get("boards")
    if not isinstance(boards, list):
        errors.append("boards must be an array")
        return errors
    package_ids: set[str] = set()
    for index, item in enumerate(boards):
        prefix = f"boards[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        package_id = item.get("package_id")
        if nonempty(package_id, f"{prefix}.package_id", errors):
            if package_id in package_ids:
                errors.append(f"duplicate package_id {package_id!r}")
            package_ids.add(package_id)

    lesson_ids: set[str] = set()
    for index, board in enumerate(boards):
        if not isinstance(board, dict):
            continue
        prefix = f"boards[{index}]"
        package_id = str(board.get("package_id", ""))
        status = board.get("status")
        if status not in PACKAGE_STATUSES:
            errors.append(
                f"{prefix}.status must be one of {', '.join(sorted(PACKAGE_STATUSES))}"
            )
        validate_identity(board.get("identity"), f"{prefix}.identity", errors)
        compatibility = board.get("compatibility")
        if not isinstance(compatibility, dict):
            errors.append(f"{prefix}.compatibility must be an object")
        else:
            nonempty(compatibility.get("idf"), f"{prefix}.compatibility.idf", errors)
            nonempty(
                compatibility.get("tirtc_sdk"),
                f"{prefix}.compatibility.tirtc_sdk",
                errors,
            )

        artifacts = board.get("artifacts", {})
        if not isinstance(artifacts, dict):
            errors.append(f"{prefix}.artifacts must be an object")
            artifacts = {}
        if status in {"adapter_verified", "hil_verified"}:
            for field in ("hardware_ir", "adapter", "config_overlay"):
                resolved = safe_registry_path(
                    registry_path,
                    artifacts.get(field),
                    f"{prefix}.artifacts.{field}",
                    errors,
                )
                if resolved is not None and not resolved.exists():
                    errors.append(f"{prefix}.artifacts.{field} does not exist")
            contracts = artifacts.get("contracts")
            if not isinstance(contracts, list) or not contracts:
                errors.append(f"{prefix}.artifacts.contracts must be a non-empty array")
            else:
                for contract_index, value in enumerate(contracts):
                    resolved = safe_registry_path(
                        registry_path,
                        value,
                        f"{prefix}.artifacts.contracts[{contract_index}]",
                        errors,
                    )
                    if resolved is not None and not resolved.is_file():
                        errors.append(
                            f"{prefix}.artifacts.contracts[{contract_index}] does not exist"
                        )

        lessons = board.get("lessons", [])
        if not isinstance(lessons, list):
            errors.append(f"{prefix}.lessons must be an array")
            continue
        for lesson_index, lesson in enumerate(lessons):
            lesson_path = f"{prefix}.lessons[{lesson_index}]"
            validate_lesson(
                lesson,
                lesson_path,
                package_id,
                package_ids,
                registry_path,
                errors,
            )
            if isinstance(lesson, dict) and isinstance(lesson.get("id"), str):
                lesson_id = lesson["id"]
                if lesson_id in lesson_ids:
                    errors.append(f"duplicate lesson id {lesson_id!r}")
                lesson_ids.add(lesson_id)
    return errors


def validate_observed_identity(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    declared = data.get("declared")
    observed = data.get("observed")
    if not isinstance(declared, dict):
        errors.append("declared must be an object")
        declared = {}
    if not isinstance(observed, dict):
        errors.append("observed must be an object")
        observed = {}
    for field in ("vendor", "model", "hardware_revision"):
        nullable_nonempty(declared.get(field), f"declared.{field}", errors)
    for field in ("target", "module"):
        nullable_nonempty(observed.get(field), f"observed.{field}", errors)
    nullable_positive_int(observed.get("flash_mb"), "observed.flash_mb", errors)
    nullable_positive_int(observed.get("psram_mb"), "observed.psram_mb", errors)
    for field, validator in (("components", validate_component), ("probes", validate_probe)):
        values = observed.get(field, [])
        if not isinstance(values, list):
            errors.append(f"observed.{field} must be an array")
            continue
        for index, item in enumerate(values):
            validator(item, f"observed.{field}[{index}]", errors)
    if not any(normalized(declared.get(field)) for field in ("vendor", "model", "hardware_revision")) and not any(
        observed.get(field) for field in ("target", "module", "components", "probes")
    ):
        errors.append("identity must contain declared board data or observed probes")
    return errors


def pair_set(values: Any) -> set[tuple[str, str]]:
    if not isinstance(values, list):
        return set()
    return {
        (normalized(item.get("kind")), normalized(item.get("model")))
        for item in values
        if isinstance(item, dict) and normalized(item.get("kind")) and normalized(item.get("model"))
    }


def probe_set(values: Any) -> set[tuple[str, str]]:
    if not isinstance(values, list):
        return set()
    return {
        (normalized(item.get("kind")), normalized(item.get("value")))
        for item in values
        if isinstance(item, dict) and normalized(item.get("kind")) and normalized(item.get("value"))
    }


def match_board(board: dict[str, Any], query: dict[str, Any]) -> dict[str, Any] | None:
    identity = board["identity"]
    declared = query.get("declared", {})
    observed = query.get("observed", {})
    conflicts: list[str] = []
    missing: list[str] = []
    reasons: list[str] = []

    package_names = {
        normalized(identity.get("model")),
        *(normalized(value) for value in identity.get("aliases", [])),
    }
    declared_model = normalized(declared.get("model"))
    model_match = bool(declared_model and declared_model in package_names)
    vendor_match = normalized(declared.get("vendor")) == normalized(identity.get("vendor")) if declared.get("vendor") else False
    revision_match = normalized(declared.get("hardware_revision")) == normalized(identity.get("hardware_revision")) if declared.get("hardware_revision") else False

    for field in ("target", "module", "flash_mb", "psram_mb"):
        expected = identity.get(field)
        actual = observed.get(field)
        if expected is not None and actual is not None:
            if normalized(expected) != normalized(actual):
                conflicts.append(f"{field} differs: expected {expected}, observed {actual}")
            else:
                reasons.append(f"{field} matched")

    expected_probes = probe_set(identity.get("probes", []))
    actual_probes = probe_set(observed.get("probes", []))
    observed_by_kind: dict[str, set[str]] = {}
    for kind, value in actual_probes:
        observed_by_kind.setdefault(kind, set()).add(value)
    for probe in identity.get("probes", []):
        if not isinstance(probe, dict) or not probe.get("required_for_exact"):
            continue
        key = (normalized(probe.get("kind")), normalized(probe.get("value")))
        if key in actual_probes:
            reasons.append(f"required probe {probe.get('kind')}={probe.get('value')} matched")
        elif key[0] in observed_by_kind:
            conflicts.append(
                f"required probe {probe.get('kind')} differs from {probe.get('value')}"
            )
        else:
            missing.append(f"required probe {probe.get('kind')}={probe.get('value')}")

    expected_components = pair_set(identity.get("components", []))
    actual_components = pair_set(observed.get("components", []))
    shared_components = sorted(expected_components.intersection(actual_components))

    if conflicts:
        classification = "component" if shared_components else "none"
    elif model_match and vendor_match and revision_match and not missing:
        classification = "exact"
    elif model_match or (model_match and vendor_match):
        classification = "probable"
        if not revision_match:
            missing.append("exact hardware revision")
    elif shared_components or expected_probes.intersection(actual_probes):
        classification = "component"
    else:
        classification = "none"

    if classification == "none":
        return None
    status = board["status"]
    if classification == "exact" and status in {"adapter_verified", "hil_verified"}:
        reuse = "registered_board"
    elif classification == "exact":
        reuse = "knowledge_only"
    elif classification == "probable":
        reuse = "candidate_only"
    else:
        reuse = "component_lessons_only"
    rank = {"exact": 3, "probable": 2, "component": 1}[classification]
    applicable_lessons = []
    for lesson in board.get("lessons", []):
        scope = lesson.get("scope")
        if classification == "exact" or scope == "generic" or (
            scope == "component" and shared_components
        ):
            applicable_lessons.append(lesson)
    return {
        "package_id": board["package_id"],
        "status": status,
        "classification": classification,
        "reuse": reuse,
        "rank": rank,
        "reasons": reasons,
        "missing": sorted(set(missing)),
        "conflicts": conflicts,
        "shared_components": [
            {"kind": kind, "model": model} for kind, model in shared_components
        ],
        "applicable_lessons": applicable_lessons,
        "artifacts": board.get("artifacts", {}) if reuse == "registered_board" else {},
    }


def match_registry(registry: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    matches = [
        match
        for board in registry.get("boards", [])
        if (match := match_board(board, query)) is not None
    ]
    matches.sort(key=lambda item: (-item["rank"], item["package_id"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "result": matches[0]["classification"] if matches else "none",
        "safe_registered_reuse": bool(
            matches and matches[0]["reuse"] == "registered_board"
        ),
        "matches": matches,
    }


def components_from_ir(data: dict[str, Any]) -> list[dict[str, str]]:
    components: list[dict[str, str]] = []
    camera = data.get("camera", {})
    if camera.get("present") is True and isinstance(camera.get("sensor"), str):
        components.append({"kind": "camera", "model": camera["sensor"]})
    for section, kind in (("audio_input", "audio_input"), ("audio_output", "audio_output")):
        value = data.get(section, {})
        for codec in value.get("codecs", []) if isinstance(value, dict) else []:
            if isinstance(codec, dict) and isinstance(codec.get("name"), str):
                components.append({"kind": kind, "model": codec["name"]})
    unique = {(normalized(item["kind"]), normalized(item["model"])): item for item in components}
    return [unique[key] for key in sorted(unique)]


def candidate_from_ir(data: dict[str, Any]) -> dict[str, Any]:
    board = data["board"]
    soc = data["soc"]
    toolchain = data["toolchain"]
    tirtc = toolchain.get("tirtc", {})
    resources = data.get("hardware_resources", {})
    contracts = [
        resources.get(field)
        for field in (
            "audio_semantic_contract",
            "video_semantic_contract",
            "runtime_semantic_contract",
        )
        if isinstance(resources.get(field), str) and resources.get(field)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "promotion_status": "candidate",
        "package_id": board["id"],
        "identity": {
            "vendor": board["vendor"],
            "model": board["model"],
            "aliases": [],
            "hardware_revision": board["hardware_revision"],
            "target": soc["target"],
            "module": soc.get("module"),
            "flash_mb": soc.get("flash_mb"),
            "psram_mb": soc.get("psram_mb"),
            "components": components_from_ir(data),
            "probes": [],
        },
        "compatibility": {
            "idf": toolchain["framework_version"],
            "tirtc_sdk": tirtc.get("version", "unknown"),
        },
        "proposed_artifacts": {
            "hardware_ir": "hardware-ir.json",
            "adapter": None,
            "config_overlay": "sdkconfig.defaults",
            "contracts": contracts,
        },
        "lessons": [],
        "promotion_requirements": [
            "resolve exact PCB revision and every required runtime probe",
            "copy project-relative Hardware IR, adapter, config overlay and contracts into the registry package",
            "bind hardware/HIL lessons to an exact artifact SHA-256",
            "add a focused regression test before promoting a generic invariant",
            "review and commit the candidate; never mutate an installed Skill automatically",
        ],
    }


def default_registry() -> Path:
    return Path(__file__).resolve().parent.parent / "knowledge" / "board-registry.json"


def load_valid_registry(path: Path) -> dict[str, Any]:
    registry = load_json(path, "board registry")
    errors = validate_registry(registry, path)
    if errors:
        raise ValueError("\n".join(f"error: {item}" for item in errors))
    return registry


def command_validate(args: argparse.Namespace) -> int:
    try:
        registry = load_json(args.registry, "board registry")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    errors = validate_registry(registry, args.registry)
    if errors:
        for item in errors:
            print(f"error: {item}", file=sys.stderr)
        return 2
    print(f"valid board registry: {args.registry} ({len(registry['boards'])} packages)")
    return 0


def command_list(args: argparse.Namespace) -> int:
    try:
        registry = load_valid_registry(args.registry)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not registry["boards"]:
        print("No curated board packages are registered.")
        return 0
    for board in registry["boards"]:
        identity = board["identity"]
        print(
            f"{board['package_id']}\t{board['status']}\t"
            f"{identity['vendor']} {identity['model']} {identity['hardware_revision']}"
        )
    return 0


def command_match(args: argparse.Namespace) -> int:
    try:
        registry = load_valid_registry(args.registry)
        query = load_json(args.identity, "board identity")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    errors = validate_observed_identity(query)
    if errors:
        for item in errors:
            print(f"error: {item}", file=sys.stderr)
        return 2
    print(json.dumps(match_registry(registry, query), indent=2, ensure_ascii=False))
    return 0


def command_init_identity(args: argparse.Namespace) -> int:
    output = args.output.resolve()
    if output.exists():
        print(f"refusing to overwrite existing file: {output}", file=sys.stderr)
        return 2
    example = Path(__file__).resolve().parent.parent / "assets" / "board-identity.example.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(example, output)
    print(f"created board identity: {output}")
    return 0


def command_candidate(args: argparse.Namespace) -> int:
    output = args.output.resolve()
    if output.exists():
        print(f"refusing to overwrite existing file: {output}", file=sys.stderr)
        return 2
    try:
        data = load_ir(args.hardware_ir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    errors = validate_ir(data) + validate_source_locations(data, args.hardware_ir.parent)
    if errors:
        for item in errors:
            print(f"error: {item}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(candidate_from_ir(data), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"created board knowledge candidate: {output}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate, match, and create candidates for ESP32 board knowledge."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("validate", "list"):
        child = subparsers.add_parser(name)
        child.add_argument("--registry", type=Path, default=default_registry())

    match_parser = subparsers.add_parser("match")
    match_parser.add_argument("--registry", type=Path, default=default_registry())
    match_parser.add_argument("--identity", type=Path, required=True)

    identity_parser = subparsers.add_parser("init-identity")
    identity_parser.add_argument("--output", type=Path, required=True)

    candidate_parser = subparsers.add_parser("candidate")
    candidate_parser.add_argument("--hardware-ir", type=Path, required=True)
    candidate_parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "validate":
        return command_validate(args)
    if args.command == "list":
        return command_list(args)
    if args.command == "match":
        return command_match(args)
    if args.command == "init-identity":
        return command_init_identity(args)
    return command_candidate(args)


if __name__ == "__main__":
    raise SystemExit(main())

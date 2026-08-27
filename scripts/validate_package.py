#!/usr/bin/env python3
"""Validate the distributable TiRTC Device Builder package without dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_SUFFIXES = {
    ".a",
    ".bin",
    ".der",
    ".elf",
    ".key",
    ".p12",
    ".pfx",
    ".pem",
}
SCAFFOLD_MARKER = "[TO" + "DO:"
OBSOLETE_SKILL_NAME = "tirtc-" + "embedded-builder"


def error(errors: list[str], message: str) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        error(errors, f"cannot read {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        error(errors, f"{path.relative_to(ROOT)} must contain a JSON object")
        return {}
    return payload


def parse_skill_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        error(errors, f"{path.relative_to(ROOT)} is missing YAML frontmatter")
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        error(errors, f"{path.relative_to(ROOT)} has unterminated YAML frontmatter")
        return {}

    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def validate_plugin(errors: list[str]) -> None:
    manifest = load_json(PLUGIN_MANIFEST, errors)
    name = manifest.get("name")
    if name != ROOT.name:
        error(errors, "plugin name must match the repository root directory")
    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER.fullmatch(version) is None:
        error(errors, "plugin version must use semantic versioning")
    if manifest.get("skills") != "./skills/":
        error(errors, "plugin skills path must be ./skills/")

    author = manifest.get("author")
    if not isinstance(author, dict) or not author.get("name"):
        error(errors, "plugin author.name is required")
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        error(errors, "plugin interface object is required")
        return
    for field in (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "defaultPrompt",
    ):
        if not interface.get(field):
            error(errors, f"plugin interface.{field} is required")


def validate_skills(errors: list[str]) -> None:
    skills_root = ROOT / "skills"
    skill_dirs = sorted(path for path in skills_root.iterdir() if path.is_dir())
    if not skill_dirs:
        error(errors, "at least one skill is required")
        return

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            error(errors, f"{skill_dir.relative_to(ROOT)} is missing SKILL.md")
            continue
        fields = parse_skill_frontmatter(skill_file, errors)
        name = fields.get("name", "")
        if name != skill_dir.name:
            error(errors, f"{skill_file.relative_to(ROOT)} name must match its directory")
        if SKILL_NAME.fullmatch(name) is None:
            error(errors, f"invalid skill name: {name!r}")
        if not fields.get("description"):
            error(errors, f"{skill_file.relative_to(ROOT)} description is required")

        openai_yaml = skill_dir / "agents" / "openai.yaml"
        if openai_yaml.is_file():
            metadata = openai_yaml.read_text(encoding="utf-8")
            if f"${name}" not in metadata:
                error(
                    errors,
                    f"{openai_yaml.relative_to(ROOT)} default prompt must mention ${name}",
                )


def validate_repository_files(errors: list[str]) -> None:
    required = (
        "README.md",
        "LICENSE",
        "NOTICE",
        "SECURITY.md",
        "CHANGELOG.md",
    )
    for relative in required:
        if not (ROOT / relative).is_file():
            error(errors, f"missing {relative}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            error(errors, f"forbidden binary or credential file: {relative}")
        if path.suffix.lower() in {".md", ".py", ".json", ".yaml", ".yml"}:
            text = path.read_text(encoding="utf-8")
            if SCAFFOLD_MARKER in text:
                error(errors, f"unfinished scaffold placeholder in {relative}")
            if OBSOLETE_SKILL_NAME in text:
                error(errors, f"obsolete skill name in {relative}")


def main() -> int:
    errors: list[str] = []
    validate_plugin(errors)
    validate_skills(errors)
    validate_repository_files(errors)
    if errors:
        print("Package validation failed:", file=sys.stderr)
        for message in errors:
            print(f"- {message}", file=sys.stderr)
        return 1
    print("Package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

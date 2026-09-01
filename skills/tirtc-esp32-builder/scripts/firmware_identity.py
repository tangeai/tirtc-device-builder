#!/usr/bin/env python3
"""Inspect the ESP-IDF application descriptor in an application BIN."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any


ESP_IMAGE_MAGIC = 0xE9
ESP_APP_DESC_MAGIC = 0xABCD5432
IMAGE_HEADER_SIZE = 24
SEGMENT_HEADER_SIZE = 8
APP_DESC_OFFSET = IMAGE_HEADER_SIZE + SEGMENT_HEADER_SIZE
APP_DESC_REQUIRED_SIZE = 176


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def descriptor_string(data: bytes, offset: int, size: int, label: str) -> str:
    raw = data[offset : offset + size]
    value = raw.split(b"\0", 1)[0]
    try:
        decoded = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"application descriptor {label} is not UTF-8") from exc
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in decoded):
        raise ValueError(f"application descriptor {label} contains control bytes")
    return decoded


def inspect_firmware(
    firmware_path: Path,
    *,
    elf_path: Path | None = None,
    expected_version: str | None = None,
) -> dict[str, Any]:
    firmware = firmware_path.expanduser().resolve()
    try:
        data = firmware.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read application BIN {firmware}: {exc}") from exc

    minimum_size = APP_DESC_OFFSET + APP_DESC_REQUIRED_SIZE
    if len(data) < minimum_size:
        raise ValueError(
            f"application BIN is truncated: need at least {minimum_size} bytes"
        )
    if data[0] != ESP_IMAGE_MAGIC:
        raise ValueError(
            f"not an ESP application image: expected magic 0x{ESP_IMAGE_MAGIC:02x}"
        )

    segment_length = struct.unpack_from("<I", data, IMAGE_HEADER_SIZE + 4)[0]
    if segment_length < APP_DESC_REQUIRED_SIZE:
        raise ValueError("first ESP image segment is too small for esp_app_desc_t")

    descriptor = data[APP_DESC_OFFSET : APP_DESC_OFFSET + APP_DESC_REQUIRED_SIZE]
    descriptor_magic = struct.unpack_from("<I", descriptor, 0)[0]
    if descriptor_magic != ESP_APP_DESC_MAGIC:
        raise ValueError(
            "first ESP image segment does not start with a valid esp_app_desc_t"
        )

    version = descriptor_string(descriptor, 16, 32, "version")
    if not version:
        raise ValueError("application descriptor version is empty")
    if expected_version is not None and version != expected_version:
        raise ValueError(
            f"firmware version mismatch: expected {expected_version!r}, got {version!r}"
        )

    elf_digest = descriptor[144:176].hex()
    result: dict[str, Any] = {
        "firmware_path": str(firmware),
        "size_bytes": len(data),
        "bin_sha256": hashlib.sha256(data).hexdigest(),
        "segment_count": data[1],
        "project_name": descriptor_string(descriptor, 48, 32, "project_name"),
        "version": version,
        "build_time": descriptor_string(descriptor, 80, 16, "time"),
        "build_date": descriptor_string(descriptor, 96, 16, "date"),
        "idf_version": descriptor_string(descriptor, 112, 32, "idf_ver"),
        "app_elf_sha256": elf_digest,
    }

    if elf_path is not None:
        elf = elf_path.expanduser().resolve()
        try:
            elf_size = elf.stat().st_size
            actual_elf_digest = sha256_file(elf)
        except OSError as exc:
            raise ValueError(f"cannot read ELF {elf}: {exc}") from exc
        if actual_elf_digest != elf_digest:
            raise ValueError(
                "ELF SHA-256 mismatch: application descriptor records "
                f"{elf_digest}, file is {actual_elf_digest}"
            )
        result.update(
            {
                "elf_path": str(elf),
                "elf_size_bytes": elf_size,
                "elf_sha256": actual_elf_digest,
            }
        )

    return result


def print_human(result: dict[str, Any]) -> None:
    fields = (
        ("firmware", "firmware_path"),
        ("project", "project_name"),
        ("version", "version"),
        ("build", "build_date"),
        ("time", "build_time"),
        ("idf", "idf_version"),
        ("size_bytes", "size_bytes"),
        ("bin_sha256", "bin_sha256"),
        ("app_elf_sha256", "app_elf_sha256"),
        ("elf", "elf_path"),
        ("elf_size_bytes", "elf_size_bytes"),
        ("elf_sha256", "elf_sha256"),
    )
    for label, key in fields:
        if key in result:
            print(f"{label}: {result[key]}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "inspect version and SHA-256 identity from an ESP-IDF application BIN"
        )
    )
    parser.add_argument("firmware", type=Path, help="ESP-IDF application BIN")
    parser.add_argument(
        "--elf",
        type=Path,
        help="matching ELF; its SHA-256 must equal app_elf_sha256 in the BIN",
    )
    parser.add_argument(
        "--expect-version",
        help="fail unless the application descriptor contains this exact version",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = inspect_firmware(
            args.firmware,
            elf_path=args.elf,
            expected_version=args.expect_version,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

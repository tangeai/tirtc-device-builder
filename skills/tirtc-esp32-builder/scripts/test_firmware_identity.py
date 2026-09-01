from __future__ import annotations

import contextlib
import hashlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from firmware_identity import (
    APP_DESC_OFFSET,
    ESP_APP_DESC_MAGIC,
    ESP_IMAGE_MAGIC,
    inspect_firmware,
    main,
)


def fixed_field(value: str, size: int) -> bytes:
    encoded = value.encode("utf-8")
    if len(encoded) >= size:
        raise ValueError("test field is too long")
    return encoded + bytes(size - len(encoded))


def application_image(elf_digest: bytes, version: str = "test-repro.1") -> bytes:
    descriptor = bytearray(176)
    struct.pack_into("<I", descriptor, 0, ESP_APP_DESC_MAGIC)
    descriptor[16:48] = fixed_field(version, 32)
    descriptor[48:80] = fixed_field("identity_test", 32)
    descriptor[80:96] = fixed_field("12:34:56", 16)
    descriptor[96:112] = fixed_field("Aug 31 2026", 16)
    descriptor[112:144] = fixed_field("v5.5.4", 32)
    descriptor[144:176] = elf_digest

    header = bytearray(24)
    header[0] = ESP_IMAGE_MAGIC
    header[1] = 1
    segment_header = struct.pack("<II", 0x3C000020, len(descriptor))
    return bytes(header) + segment_header + bytes(descriptor)


class FirmwareIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.elf = self.root / "identity_test.elf"
        self.elf.write_bytes(b"synthetic ELF used by the unit test\n")
        self.elf_digest = hashlib.sha256(self.elf.read_bytes()).digest()
        self.firmware = self.root / "identity_test.bin"
        self.firmware.write_bytes(application_image(self.elf_digest))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_reads_version_and_matches_full_elf_hash(self) -> None:
        result = inspect_firmware(
            self.firmware,
            elf_path=self.elf,
            expected_version="test-repro.1",
        )
        self.assertEqual("identity_test", result["project_name"])
        self.assertEqual("test-repro.1", result["version"])
        self.assertEqual(hashlib.sha256(self.elf.read_bytes()).hexdigest(), result["elf_sha256"])
        self.assertEqual(hashlib.sha256(self.firmware.read_bytes()).hexdigest(), result["bin_sha256"])

    def test_json_cli_output_is_machine_readable(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([str(self.firmware), "--json"])
        self.assertEqual(0, status)
        self.assertEqual("test-repro.1", json.loads(output.getvalue())["version"])

    def test_expected_version_mismatch_fails(self) -> None:
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            status = main(
                [str(self.firmware), "--expect-version", "test-fix.1"]
            )
        self.assertEqual(2, status)
        self.assertIn("firmware version mismatch", error.getvalue())

    def test_wrong_elf_fails(self) -> None:
        wrong_elf = self.root / "wrong.elf"
        wrong_elf.write_bytes(b"different ELF\n")
        with self.assertRaisesRegex(ValueError, "ELF SHA-256 mismatch"):
            inspect_firmware(self.firmware, elf_path=wrong_elf)

    def test_rejects_invalid_image_and_descriptor_magic(self) -> None:
        invalid_image = self.root / "invalid-image.bin"
        invalid_image.write_bytes(bytes(APP_DESC_OFFSET + 176))
        with self.assertRaisesRegex(ValueError, "not an ESP application image"):
            inspect_firmware(invalid_image)

        invalid_descriptor = bytearray(self.firmware.read_bytes())
        invalid_descriptor[APP_DESC_OFFSET : APP_DESC_OFFSET + 4] = bytes(4)
        invalid_descriptor_path = self.root / "invalid-descriptor.bin"
        invalid_descriptor_path.write_bytes(invalid_descriptor)
        with self.assertRaisesRegex(ValueError, "valid esp_app_desc_t"):
            inspect_firmware(invalid_descriptor_path)


if __name__ == "__main__":
    unittest.main()

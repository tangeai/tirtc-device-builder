from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from board_registry import (
    candidate_from_ir,
    match_registry,
    validate_observed_identity,
    validate_registry,
)


def board(status: str = "knowledge_only") -> dict:
    return {
        "package_id": "vendor_media_board_rev_a_gc2145",
        "status": status,
        "identity": {
            "vendor": "Vendor",
            "model": "Media Board",
            "aliases": ["Media Board S3"],
            "hardware_revision": "Rev A",
            "target": "esp32s3",
            "module": "ESP32-S3-WROOM-1-N16R8",
            "flash_mb": 16,
            "psram_mb": 8,
            "components": [
                {"kind": "camera", "model": "GC2145"},
                {"kind": "audio_input", "model": "ES7210"},
            ],
            "probes": [
                {
                    "kind": "camera_pid",
                    "value": "0x2145",
                    "required_for_exact": True,
                }
            ],
        },
        "compatibility": {"idf": "5.5.x", "tirtc_sdk": "2.3.0"},
        "artifacts": {},
        "lessons": [
            {
                "id": "gc2145_psram_dma_requires_hil",
                "scope": "component",
                "subject": "camera:GC2145",
                "guidance": "Treat direct PSRAM DMA as unverified until frame integrity passes HIL.",
                "action": "block_until_hil",
                "verification": "hil_verified",
                "applies_to": {"kind": "camera", "model": "GC2145"},
                "evidence": [
                    {
                        "board_package_id": "vendor_media_board_rev_a_gc2145",
                        "artifact_sha256": "a" * 64,
                    }
                ],
            }
        ],
    }


def identity(
    *,
    model: str = "Media Board",
    revision: str | None = "Rev A",
    camera_pid: str | None = "0x2145",
) -> dict:
    probes = []
    if camera_pid is not None:
        probes.append(
            {
                "kind": "camera_pid",
                "value": camera_pid,
                "required_for_exact": True,
            }
        )
    return {
        "schema_version": 1,
        "declared": {
            "vendor": "Vendor",
            "model": model,
            "hardware_revision": revision,
        },
        "observed": {
            "target": "esp32s3",
            "module": "ESP32-S3-WROOM-1-N16R8",
            "flash_mb": 16,
            "psram_mb": 8,
            "components": [{"kind": "camera", "model": "GC2145"}],
            "probes": probes,
        },
    }


class BoardRegistryTests(unittest.TestCase):
    def test_packaged_waveshare_is_discoverable_but_not_reusable(self) -> None:
        path = Path(__file__).resolve().parent.parent / "knowledge/board-registry.json"
        registry = json.loads(path.read_text())
        self.assertEqual([], validate_registry(registry, path))
        query = identity(model="ESP32-P4-WIFI6-Touch-LCD-3.5", revision=None, camera_pid=None)
        query["declared"]["vendor"] = "Waveshare"
        query["observed"] = {"target": "esp32p4", "flash_mb": 16, "psram_mb": 32}
        result = match_registry(registry, query)
        self.assertEqual("probable", result["result"])
        self.assertFalse(result["safe_registered_reuse"])
        match = result["matches"][0]
        self.assertTrue(match["knowledge_refs"])
        self.assertEqual({}, match["artifacts"])
        self.assertEqual([], match["applicable_lessons"])
        query["declared"]["hardware_revision"] = "V1.0"
        self.assertEqual("probable", match_registry(registry, query)["result"])
        query["observed"]["psram_mb"] = 8
        self.assertFalse(match_registry(registry, query)["safe_registered_reuse"])

    def test_unknown_revision_is_only_valid_for_knowledge(self) -> None:
        item = board()
        item["identity"]["hardware_revision"] = None
        path = Path("/tmp/registry.json")
        self.assertEqual([], validate_registry({"schema_version": 1, "boards": [item]}, path))
        item["status"] = "adapter_verified"
        errors = validate_registry({"schema_version": 1, "boards": [item]}, path)
        self.assertTrue(any("hardware_revision" in error for error in errors))

    def test_knowledge_reference_cannot_escape_or_be_missing(self) -> None:
        item = board()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            for ref in ("../outside.md", "/tmp/outside.md", "missing.md"):
                item["knowledge_refs"] = [ref]
                errors = validate_registry({"schema_version": 1, "boards": [item]}, path)
                self.assertTrue(any("knowledge_refs" in error for error in errors))

    def test_component_match_does_not_inherit_board_source_map(self) -> None:
        item = board()
        item["knowledge_refs"] = ["board-only.md"]
        result = match_registry({"schema_version": 1, "boards": [item]}, identity(model="Other"))
        self.assertEqual("component", result["result"])
        self.assertEqual([], result["matches"][0]["knowledge_refs"])

    def test_empty_packaged_registry_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board-registry.json"
            self.assertEqual(
                [], validate_registry({"schema_version": 1, "boards": []}, path)
            )

    def test_exact_knowledge_match_does_not_install_adapter(self) -> None:
        registry = {"schema_version": 1, "boards": [board()]}
        result = match_registry(registry, identity())
        self.assertEqual("exact", result["result"])
        self.assertFalse(result["safe_registered_reuse"])
        self.assertEqual("knowledge_only", result["matches"][0]["reuse"])
        self.assertEqual(1, len(result["matches"][0]["applicable_lessons"]))

    def test_exact_verified_adapter_can_select_registered_board(self) -> None:
        registry_board = board("adapter_verified")
        registry_board["artifacts"] = {
            "hardware_ir": "boards/board/hardware-ir.json",
            "adapter": "boards/board/adapter",
            "config_overlay": "boards/board/sdkconfig.defaults",
            "contracts": ["boards/board/board-audio-contract.json"],
        }
        result = match_registry(
            {"schema_version": 1, "boards": [registry_board]}, identity()
        )
        self.assertTrue(result["safe_registered_reuse"])
        self.assertEqual("registered_board", result["matches"][0]["reuse"])

    def test_missing_required_probe_is_only_probable(self) -> None:
        result = match_registry(
            {"schema_version": 1, "boards": [board()]},
            identity(camera_pid=None),
        )
        self.assertEqual("probable", result["result"])
        self.assertIn(
            "required probe camera_pid=0x2145", result["matches"][0]["missing"]
        )

    def test_conflicting_probe_prevents_board_reuse(self) -> None:
        result = match_registry(
            {"schema_version": 1, "boards": [board()]},
            identity(camera_pid="0x009b"),
        )
        self.assertEqual("component", result["result"])
        self.assertFalse(result["safe_registered_reuse"])
        self.assertTrue(result["matches"][0]["conflicts"])

    def test_same_component_on_another_board_reuses_only_component_lessons(self) -> None:
        query = identity(model="Another Board")
        query["declared"]["vendor"] = "Other Vendor"
        result = match_registry({"schema_version": 1, "boards": [board()]}, query)
        self.assertEqual("component", result["result"])
        self.assertEqual(
            "component_lessons_only", result["matches"][0]["reuse"]
        )

    def test_generic_lesson_requires_two_boards_and_regression(self) -> None:
        registry_board = board()
        registry_board["lessons"][0].update(
            {
                "scope": "generic",
                "applies_to": {},
                "verification": "corroborated",
                "regression_test": "tests/missing.py",
                "evidence": [
                    {"board_package_id": registry_board["package_id"]}
                ],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board-registry.json"
            errors = validate_registry(
                {"schema_version": 1, "boards": [registry_board]}, path
            )
        self.assertTrue(any("two independent" in item for item in errors))
        self.assertTrue(any("regression_test does not exist" in item for item in errors))

    def test_identity_requires_declared_or_observed_facts(self) -> None:
        value = {
            "schema_version": 1,
            "declared": {"vendor": None, "model": None, "hardware_revision": None},
            "observed": {
                "target": None,
                "module": None,
                "flash_mb": None,
                "psram_mb": None,
                "components": [],
                "probes": [],
            },
        }
        self.assertTrue(validate_observed_identity(value))

    def test_hardware_ir_becomes_unpromoted_candidate(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "hardware-ir-v2.example.json"
        )
        data = json.loads(source.read_text(encoding="utf-8"))
        data["board"]["hardware_revision"] = "Rev A"
        data["camera"].update({"present": True, "sensor": "GC2145"})
        candidate = candidate_from_ir(copy.deepcopy(data))
        self.assertEqual("candidate", candidate["promotion_status"])
        self.assertEqual("Rev A", candidate["identity"]["hardware_revision"])
        self.assertIn(
            {"kind": "camera", "model": "GC2145"},
            candidate["identity"]["components"],
        )
        self.assertEqual([], candidate["lessons"])


if __name__ == "__main__":
    unittest.main()

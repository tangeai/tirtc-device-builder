from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("hardware_ir.py")
SPEC = importlib.util.spec_from_file_location("hardware_ir", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
EXAMPLE = SCRIPT.parent.parent / "assets" / "hardware-ir.example.json"


class HardwareIrTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_example_is_valid_but_needs_confirmation(self) -> None:
        self.assertEqual([], MODULE.validate_ir(self.ir))
        assessment = MODULE.assess_ir(self.ir)
        self.assertEqual(
            "NEEDS_CONFIRMATION",
            assessment["features"]["h5_live_video"]["status"],
        )
        self.assertEqual(
            "NEEDS_CONFIRMATION", assessment["features"]["ai_talk"]["status"]
        )

    def test_complete_media_path_is_ready_to_port(self) -> None:
        ready = copy.deepcopy(self.ir)
        ready["board"]["hardware_revision"] = "A"
        ready["toolchain"]["verification"] = "corroborated"
        ready["camera"].update(
            {
                "present": True,
                "sensor": "verified-camera",
                "interface": "dvp",
                "h264": {
                    "available": True,
                    "output_format": "h264_annex_b",
                    "key_frame_control": True,
                    "verification": "corroborated",
                },
            }
        )
        for section in ("audio_input", "audio_output"):
            ready[section].update(
                {
                    "present": True,
                    "interface": "i2s",
                    "codecs": [
                        {
                            "name": "alaw",
                            "sample_rates_hz": [8000],
                            "verification": "corroborated",
                        }
                    ],
                }
            )
        self.assertEqual([], MODULE.validate_ir(ready))
        assessment = MODULE.assess_ir(ready)
        statuses = {
            item["status"] for item in assessment["features"].values()
        }
        self.assertEqual({"READY_TO_PORT"}, statuses)
        self.assertEqual("READY_TO_PORT", assessment["project_gate"]["status"])

    def test_confirmed_missing_h264_is_blocked(self) -> None:
        blocked = copy.deepcopy(self.ir)
        blocked["camera"]["present"] = True
        blocked["camera"]["h264"]["available"] = False
        assessment = MODULE.assess_ir(blocked)
        self.assertEqual(
            "BLOCKED", assessment["features"]["h5_live_video"]["status"]
        )

    def test_unknown_source_reference_is_invalid(self) -> None:
        invalid = copy.deepcopy(self.ir)
        invalid["camera"]["source_refs"] = ["missing-source"]
        errors = MODULE.validate_ir(invalid)
        self.assertTrue(any("unknown source" in error for error in errors))

    def test_mismatched_tirtc_platform_blocks_project(self) -> None:
        invalid_target = copy.deepcopy(self.ir)
        invalid_target["board"]["hardware_revision"] = "A"
        invalid_target["toolchain"]["verification"] = "corroborated"
        invalid_target["toolchain"]["tirtc"]["platform"] = "espressif-esp32p4"
        assessment = MODULE.assess_ir(invalid_target)
        self.assertEqual("BLOCKED", assessment["project_gate"]["status"])


if __name__ == "__main__":
    unittest.main()

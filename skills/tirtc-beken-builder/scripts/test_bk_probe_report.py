from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("bk_probe_report.py")
SPEC = importlib.util.spec_from_file_location("bk_probe_report", MODULE_PATH)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class ProbeReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = probe.template()

    def test_template_is_valid(self) -> None:
        self.assertEqual([], probe.validate(self.report))

    def test_rejects_secret_fields(self) -> None:
        self.report["wifi_password"] = "not-allowed"
        self.assertIn(
            "secret-bearing field is forbidden: wifi_password",
            probe.validate(self.report),
        )

    def test_rejects_non_boolean_integration_without_crashing(self) -> None:
        self.report["integration"]["session_arbiter"] = []
        self.assertIn(
            "integration.session_arbiter must be true, false, or null",
            probe.validate(self.report),
        )

    def test_display_without_touch_recommends_status_ui(self) -> None:
        self.report["display"].update(
            {"state": "verified", "width_px": 480, "height_px": 480, "test": "pass"}
        )
        result = probe.assess(self.report)
        self.assertEqual("SUPPORTED", result["capabilities"]["display_ui"]["status"])
        self.assertEqual("UNKNOWN", result["capabilities"]["touch_ui"]["status"])
        self.assertIn("no click targets", result["capabilities"]["recommended_ui"]["reason"])

    def test_audio_hardware_is_candidate_until_integration_passes(self) -> None:
        self.report["requested_features"] = ["h5_audio"]
        self.report["audio"]["microphone"].update(
            {"state": "verified", "sample_rates_hz": [16000], "sample_bits": [16], "test": "pass"}
        )
        result = probe.assess(self.report)
        self.assertEqual("READY_TO_PORT", result["overall"])
        self.assertEqual("CANDIDATE", result["requested"]["h5_audio"]["status"])
        self.report["integration"].update(
            {"tirtc_sdk_compatible": True, "audio_uplink_pipeline": True}
        )
        result = probe.assess(self.report)
        self.assertEqual("READY", result["overall"])
        self.assertEqual("SUPPORTED", result["requested"]["h5_audio"]["status"])

    def test_duplex_requires_reference_and_aec_test(self) -> None:
        self.report["requested_features"] = ["ai_talk"]
        for endpoint in ("microphone", "speaker"):
            self.report["audio"][endpoint].update({"state": "verified", "test": "pass"})
        self.report["audio"]["microphone"]["sample_rates_hz"] = [16000]
        self.report["audio"]["duplex"].update(
            {"simultaneous": True, "playback_reference": False, "aec_available": True, "aec_test": "pass"}
        )
        result = probe.assess(self.report)
        self.assertEqual("BLOCKED", result["overall"])
        self.assertEqual("BLOCKED", result["requested"]["ai_talk"]["status"])

    def test_collect_uses_last_complete_report(self) -> None:
        older = copy.deepcopy(self.report)
        older["identity"]["chip_revision"] = "old"
        newest = copy.deepcopy(self.report)
        newest["identity"]["chip_revision"] = "new"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "serial.log"
            output = root / "report.json"
            source.write_text(
                "boot\n"
                + probe.PREFIX
                + json.dumps(older)
                + "\n"
                + probe.PREFIX
                + "{broken\n"
                + probe.PREFIX
                + json.dumps(newest)
                + "\n",
                encoding="utf-8",
            )
            args = type("Args", (), {"input": str(source), "output": str(output)})()
            self.assertEqual(0, probe.command_collect(args))
            self.assertEqual("new", json.loads(output.read_text())["identity"]["chip_revision"])


if __name__ == "__main__":
    unittest.main()

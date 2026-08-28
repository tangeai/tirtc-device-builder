from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("hardware_ir.py")
SPEC = importlib.util.spec_from_file_location("hardware_ir", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
ASSETS = SCRIPT.parent.parent / "assets"
EXAMPLE_V1 = ASSETS / "hardware-ir.example.json"
EXAMPLE_V2 = ASSETS / "hardware-ir-v2.example.json"
ARTIFACT_A = "a" * 64
ARTIFACT_B = "b" * 64


def ready_resources(ir: dict) -> None:
    resources = ir["hardware_resources"]
    resources["i2c"].update(
        {
            "used": True,
            "driver_family": "legacy",
            "single_driver_family": True,
            "verification": "corroborated",
        }
    )
    resources["i2s"].update(
        {
            "used": True,
            "controller_and_gpio_ownership_resolved": True,
            "verification": "corroborated",
        }
    )
    resources["audio_channel_mapping"].update(
        {
            "required": True,
            "resolved": True,
            "verification": "corroborated",
        }
    )
    resources["camera_realtime"].update(
        {"pipeline_safe": True, "verification": "corroborated"}
    )
    resources["memory"].update(
        {"startup_and_media_budgeted": True, "verification": "corroborated"}
    )


def ready_onboarding(ir: dict) -> None:
    onboarding = ir["onboarding"]
    onboarding["wifi_credentials"].update(
        {
            "selected_method": "softap-main",
            "methods": [
                {
                    "id": "softap-main",
                    "type": "softap",
                    "available": True,
                    "verification": "corroborated",
                    "source_refs": ["board-materials"],
                }
            ],
            "credentials_committed_to_source": False,
            "reprovisioning_defined": True,
        }
    )
    onboarding["device_binding"].update(
        {
            "selected_method": "verification-code",
            "methods": [
                {
                    "id": "verification-code",
                    "type": "verification_code",
                    "available": True,
                    "verification": "corroborated",
                    "source_refs": ["board-materials"],
                }
            ],
            "credentials_committed_to_source": False,
            "stored_credential_state_handled": True,
            "clear_binding_control": True,
        }
    )


def ready_audio(ir: dict) -> None:
    for section in ("audio_input", "audio_output"):
        ir[section].update(
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


def ready_v2(codec: str = "mjpeg") -> dict:
    ir = json.loads(EXAMPLE_V2.read_text(encoding="utf-8"))
    ir["board"]["hardware_revision"] = "A"
    ir["toolchain"]["verification"] = "corroborated"
    output_formats = {
        "mjpeg": "jpeg_complete_frames",
        "h264": "h264_annex_b_access_units",
        "h265": "h265_annex_b_access_units",
    }
    ir["camera"].update(
        {
            "present": True,
            "sensor": "evidenced-camera",
            "interface": "dvp",
            "selected_video_profile": f"{codec}-main",
            "video_profiles": [
                {
                    "id": f"{codec}-main",
                    "codec": codec,
                    "available": True,
                    "output_format": output_formats[codec],
                    "refresh_frame_control": True,
                    "stream_id": 11,
                    "verification": "corroborated",
                    "source_refs": ["board-materials"],
                }
            ],
        }
    )
    ready_audio(ir)
    ready_resources(ir)
    ready_onboarding(ir)
    return ir


def mark_build_verified(ir: dict) -> None:
    for section in ("audio_input", "audio_output"):
        for codec in ir[section]["codecs"]:
            codec["verification"] = "build_verified"
    for profile in ir["camera"]["video_profiles"]:
        profile["verification"] = "build_verified"
    resources = ir["hardware_resources"]
    for section in (
        "i2c",
        "i2s",
        "audio_channel_mapping",
        "camera_realtime",
        "memory",
    ):
        resources[section]["verification"] = "build_verified"


class HardwareIrV2Test(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = json.loads(EXAMPLE_V2.read_text(encoding="utf-8"))

    def test_example_is_valid_but_needs_confirmation(self) -> None:
        self.assertEqual([], MODULE.validate_ir(self.ir))
        assessment = MODULE.assess_ir(self.ir)
        self.assertEqual(
            "NEEDS_CONFIRMATION",
            assessment["features"]["h5_live_video"]["status"],
        )
        self.assertEqual(
            "NEEDS_CONFIRMATION", assessment["project_gate"]["status"]
        )

    def test_selected_mjpeg_profile_is_ready_without_h264(self) -> None:
        ready = ready_v2("mjpeg")
        self.assertEqual([], MODULE.validate_ir(ready))
        assessment = MODULE.assess_ir(ready)
        statuses = {
            item["status"] for item in assessment["features"].values()
        }
        self.assertEqual({"READY_TO_PORT"}, statuses)
        self.assertEqual("mjpeg", assessment["selected_video_profile"]["codec"])
        self.assertEqual("READY_TO_PORT", assessment["project_gate"]["status"])
        self.assertEqual("intake", assessment["phase"])

    def test_intake_plan_does_not_claim_build_verification(self) -> None:
        planned = ready_v2("mjpeg")
        assessment = MODULE.assess_ir(
            planned, artifact_sha256=ARTIFACT_A, phase="build"
        )
        self.assertEqual(
            "NEEDS_CONFIRMATION", assessment["project_gate"]["status"]
        )
        self.assertEqual(
            "NEEDS_CONFIRMATION",
            assessment["features"]["h5_live_video"]["status"],
        )

    def test_build_phase_requires_an_exact_artifact(self) -> None:
        built = ready_v2("mjpeg")
        mark_build_verified(built)
        assessment = MODULE.assess_ir(built, phase="build")
        self.assertEqual(
            "NEEDS_CONFIRMATION", assessment["project_gate"]["status"]
        )
        self.assertEqual(
            "BUILD_VERIFIED",
            assessment["features"]["h5_live_video"]["status"],
        )

    def test_build_phase_passes_build_verified_paths(self) -> None:
        built = ready_v2("mjpeg")
        mark_build_verified(built)
        assessment = MODULE.assess_ir(
            built, artifact_sha256=ARTIFACT_A, phase="build"
        )
        statuses = {item["status"] for item in assessment["features"].values()}
        self.assertEqual({"BUILD_VERIFIED"}, statuses)
        self.assertEqual("BUILD_VERIFIED", assessment["project_gate"]["status"])
        self.assertEqual("build", assessment["phase"])

    def test_each_contract_video_profile_has_its_own_validator(self) -> None:
        for codec in ("mjpeg", "h264", "h265"):
            with self.subTest(codec=codec):
                assessment = MODULE.assess_ir(ready_v2(codec))
                self.assertEqual(
                    "READY_TO_PORT",
                    assessment["features"]["h5_live_video"]["status"],
                )

    def test_wrong_output_format_blocks_only_selected_profile(self) -> None:
        blocked = ready_v2("mjpeg")
        blocked["camera"]["video_profiles"][0]["output_format"] = (
            "h264_annex_b_access_units"
        )
        assessment = MODULE.assess_ir(blocked)
        self.assertEqual(
            "BLOCKED", assessment["features"]["h5_live_video"]["status"]
        )

    def test_mixed_i2c_driver_families_block_project(self) -> None:
        blocked = ready_v2()
        blocked["hardware_resources"]["i2c"]["single_driver_family"] = False
        assessment = MODULE.assess_ir(blocked)
        self.assertEqual("BLOCKED", assessment["project_gate"]["status"])

    def test_unresolved_i2s_ownership_blocks_audio_features(self) -> None:
        blocked = ready_v2()
        blocked["hardware_resources"]["i2s"][
            "controller_and_gpio_ownership_resolved"
        ] = False
        assessment = MODULE.assess_ir(blocked)
        self.assertEqual(
            "BLOCKED", assessment["features"]["h5_live_audio"]["status"]
        )
        self.assertEqual(
            "BLOCKED", assessment["features"]["h5_talkback"]["status"]
        )

    def test_missing_binding_state_handling_blocks_project(self) -> None:
        blocked = ready_v2()
        blocked["onboarding"]["device_binding"][
            "stored_credential_state_handled"
        ] = False
        assessment = MODULE.assess_ir(blocked)
        self.assertEqual("BLOCKED", assessment["project_gate"]["status"])

    def test_factory_nvs_is_ready_when_softap_is_unavailable(self) -> None:
        ready = ready_v2()
        ready["onboarding"]["wifi_credentials"].update(
            {
                "selected_method": "factory-nvs",
                "methods": [
                    {
                        "id": "softap",
                        "type": "softap",
                        "available": False,
                        "verification": "corroborated",
                        "source_refs": ["board-materials"],
                    },
                    {
                        "id": "factory-nvs",
                        "type": "factory_nvs",
                        "available": True,
                        "verification": "corroborated",
                        "source_refs": ["board-materials"],
                    },
                ],
                "credentials_committed_to_source": False,
                "reprovisioning_defined": True,
            }
        )
        assessment = MODULE.assess_ir(ready)
        self.assertEqual("READY_TO_PORT", assessment["project_gate"]["status"])
        self.assertEqual(
            "factory_nvs", assessment["selected_wifi_method"]["type"]
        )

    def test_credentials_committed_to_source_block_project(self) -> None:
        blocked = ready_v2()
        blocked["onboarding"]["wifi_credentials"][
            "credentials_committed_to_source"
        ] = True
        assessment = MODULE.assess_ir(blocked)
        self.assertEqual("BLOCKED", assessment["project_gate"]["status"])

    def test_factory_binding_is_ready_without_verification_code(self) -> None:
        ready = ready_v2()
        ready["onboarding"]["device_binding"].update(
            {
                "selected_method": "factory-bound",
                "methods": [
                    {
                        "id": "factory-bound",
                        "type": "factory_bound",
                        "available": True,
                        "verification": "corroborated",
                        "source_refs": ["board-materials"],
                    }
                ],
                "credentials_committed_to_source": False,
                "stored_credential_state_handled": True,
                "clear_binding_control": True,
            }
        )
        assessment = MODULE.assess_ir(ready)
        self.assertEqual("READY_TO_PORT", assessment["project_gate"]["status"])
        self.assertEqual(
            "factory_bound", assessment["selected_binding_method"]["type"]
        )

    def test_device_credentials_committed_to_source_block_project(self) -> None:
        blocked = ready_v2()
        blocked["onboarding"]["device_binding"][
            "credentials_committed_to_source"
        ] = True
        assessment = MODULE.assess_ir(blocked)
        self.assertEqual("BLOCKED", assessment["project_gate"]["status"])

    def test_hil_status_requires_matching_artifact_evidence(self) -> None:
        ready = ready_v2()
        mark_build_verified(ready)
        ready["runtime_evidence"] = [
            {
                "artifact_sha256": ARTIFACT_A,
                "acceptance_levels": ["L2", "L3", "L4", "L5", "L6"],
                "features": [
                    "h5_live_audio",
                    "h5_live_video",
                    "h5_talkback",
                    "ai_talk",
                ],
                "source_refs": ["board-materials"],
            }
        ]
        unmatched = MODULE.assess_ir(
            ready, artifact_sha256=ARTIFACT_B, phase="hil"
        )
        matched = MODULE.assess_ir(
            ready, artifact_sha256=ARTIFACT_A, phase="hil"
        )
        self.assertEqual(
            "BUILD_VERIFIED", unmatched["features"]["h5_live_video"]["status"]
        )
        self.assertEqual(
            "HIL_VERIFIED", matched["features"]["h5_live_video"]["status"]
        )
        self.assertEqual("HIL_VERIFIED", matched["features"]["ai_talk"]["status"])
        self.assertEqual("HIL_VERIFIED", matched["project_gate"]["status"])

    def test_cli_strict_build_phase(self) -> None:
        built = ready_v2("mjpeg")
        mark_build_verified(built)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hardware-ir.json"
            path.write_text(json.dumps(built), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "assess",
                    str(path),
                    "--phase",
                    "build",
                    "--artifact-sha256",
                    ARTIFACT_A,
                    "--strict",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("build", json.loads(result.stdout)["phase"])

    def test_invalid_runtime_artifact_sha_is_rejected(self) -> None:
        invalid = ready_v2()
        invalid["runtime_evidence"] = [
            {
                "artifact_sha256": "not-a-sha",
                "acceptance_levels": ["L5"],
                "features": ["h5_live_video"],
                "source_refs": ["board-materials"],
            }
        ]
        errors = MODULE.validate_ir(invalid)
        self.assertTrue(any("artifact_sha256" in error for error in errors))

    def test_unknown_source_reference_is_invalid(self) -> None:
        invalid = ready_v2()
        invalid["camera"]["video_profiles"][0]["source_refs"] = [
            "missing-source"
        ]
        errors = MODULE.validate_ir(invalid)
        self.assertTrue(any("unknown source" in error for error in errors))


class HardwareIrV1CompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = json.loads(EXAMPLE_V1.read_text(encoding="utf-8"))

    def test_v1_example_remains_valid(self) -> None:
        self.assertEqual([], MODULE.validate_ir(self.ir))

    def test_v1_complete_h264_path_remains_ready(self) -> None:
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
        ready_audio(ready)
        assessment = MODULE.assess_ir(ready)
        statuses = {
            item["status"] for item in assessment["features"].values()
        }
        self.assertEqual({"READY_TO_PORT"}, statuses)

    def test_mismatched_tirtc_platform_blocks_project(self) -> None:
        invalid_target = copy.deepcopy(self.ir)
        invalid_target["board"]["hardware_revision"] = "A"
        invalid_target["toolchain"]["verification"] = "corroborated"
        invalid_target["toolchain"]["tirtc"]["platform"] = "espressif-esp32p4"
        assessment = MODULE.assess_ir(invalid_target)
        self.assertEqual("BLOCKED", assessment["project_gate"]["status"])


if __name__ == "__main__":
    unittest.main()

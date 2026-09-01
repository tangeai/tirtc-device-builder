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
SEMANTIC_GATE = ("SATISFIED", "semantic gate passed", 3)


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
    resources["duplex_audio"].update(
        {
            "simultaneous_capture_playback": True,
            "playback_reference_available": True,
            "aec_implementation_available": True,
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
                    "ssid_prefix": "TiRTC-",
                    "auth_mode": "open",
                    "ipv4_address": "192.168.6.1",
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
        "duplex_audio",
        "camera_realtime",
        "memory",
    ):
        resources[section]["verification"] = "build_verified"


def record_build_artifacts(ir: dict, *artifacts: str) -> None:
    ir["build_evidence"] = {
        "artifacts": [
            {
                "path": f"build/{index}.elf",
                "size_bytes": 123,
                "sha256": artifact,
            }
            for index, artifact in enumerate(artifacts)
        ]
    }


def assess_with_semantic_gates(ir: dict, **kwargs: object) -> dict:
    return MODULE.assess_ir(
        ir,
        audio_gate=SEMANTIC_GATE,
        aec_gate=SEMANTIC_GATE,
        business_gate=SEMANTIC_GATE,
        video_gate=SEMANTIC_GATE,
        runtime_gate=SEMANTIC_GATE,
        **kwargs,
    )


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
            "BLOCKED", assessment["project_gate"]["status"]
        )
        self.assertEqual(
            "NEEDS_CONFIRMATION",
            assessment["features"]["h5_live_video"]["status"],
        )

    def test_build_phase_requires_an_exact_artifact(self) -> None:
        built = ready_v2("mjpeg")
        mark_build_verified(built)
        assessment = assess_with_semantic_gates(built, phase="build")
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
        record_build_artifacts(built, ARTIFACT_A)
        assessment = assess_with_semantic_gates(
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

    def test_aec_required_features_block_without_reference_path(self) -> None:
        blocked = ready_v2()
        blocked["hardware_resources"]["duplex_audio"][
            "playback_reference_available"
        ] = False
        assessment = MODULE.assess_ir(blocked)
        for feature in ("ai_talk", "device_call", "wechat_voip"):
            self.assertEqual("BLOCKED", assessment["features"][feature]["status"])

    def test_aec_required_features_need_explicit_build_gate(self) -> None:
        built = ready_v2()
        mark_build_verified(built)
        record_build_artifacts(built, ARTIFACT_A)
        assessment = MODULE.assess_ir(
            built,
            artifact_sha256=ARTIFACT_A,
            phase="build",
            audio_gate=SEMANTIC_GATE,
            video_gate=SEMANTIC_GATE,
            runtime_gate=SEMANTIC_GATE,
        )
        for feature in ("ai_talk", "device_call", "wechat_voip"):
            self.assertEqual("BLOCKED", assessment["features"][feature]["status"])

    def test_business_gate_blocks_calls_without_blocking_h5(self) -> None:
        built = ready_v2()
        mark_build_verified(built)
        record_build_artifacts(built, ARTIFACT_A)
        assessment = MODULE.assess_ir(
            built,
            artifact_sha256=ARTIFACT_A,
            phase="build",
            audio_gate=SEMANTIC_GATE,
            aec_gate=SEMANTIC_GATE,
            video_gate=SEMANTIC_GATE,
            runtime_gate=SEMANTIC_GATE,
            business_gate=("BLOCKED", "business gate failed", 0),
        )
        for feature in ("h5_live_audio", "h5_live_video", "h5_talkback", "ai_talk"):
            self.assertEqual("BUILD_VERIFIED", assessment["features"][feature]["status"])
        for feature in ("device_call", "wechat_voip"):
            self.assertEqual("BLOCKED", assessment["features"][feature]["status"])

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

    def test_softap_contract_is_required(self) -> None:
        cases = {
            "ssid_prefix": "Other-",
            "auth_mode": "wpa2_psk",
            "ipv4_address": "192.168.4.1",
        }
        for field, invalid_value in cases.items():
            with self.subTest(field=field):
                blocked = ready_v2()
                method = blocked["onboarding"]["wifi_credentials"]["methods"][0]
                method[field] = invalid_value
                assessment = MODULE.assess_ir(blocked)
                self.assertEqual("BLOCKED", assessment["project_gate"]["status"])
                self.assertIn(
                    "SoftAP", " ".join(assessment["project_gate"]["reasons"])
                )

    def test_missing_softap_contract_needs_confirmation(self) -> None:
        incomplete = ready_v2()
        method = incomplete["onboarding"]["wifi_credentials"]["methods"][0]
        del method["ipv4_address"]
        assessment = MODULE.assess_ir(incomplete)
        self.assertEqual(
            "NEEDS_CONFIRMATION", assessment["project_gate"]["status"]
        )
        self.assertIn(
            "192.168.6.1", " ".join(assessment["project_gate"]["reasons"])
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
        record_build_artifacts(ready, ARTIFACT_A, ARTIFACT_B)
        ready["runtime_evidence"] = [
            {
                "artifact_sha256": ARTIFACT_A,
                "acceptance_levels": ["L2", "L3", "L4", "L5", "L6"],
                "features": [
                    "h5_live_audio",
                    "h5_live_video",
                    "h5_talkback",
                    "ai_talk",
                    "device_call",
                    "wechat_voip",
                ],
                "source_refs": ["board-materials"],
            }
        ]
        unmatched = assess_with_semantic_gates(
            ready, artifact_sha256=ARTIFACT_B, phase="hil"
        )
        matched = assess_with_semantic_gates(
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

    def test_cli_strict_build_phase_requires_semantic_contracts(self) -> None:
        built = ready_v2("mjpeg")
        mark_build_verified(built)
        record_build_artifacts(built, ARTIFACT_A)
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
        self.assertEqual(3, result.returncode, result.stderr)
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

    def test_invalid_build_artifact_record_is_rejected(self) -> None:
        invalid = ready_v2()
        invalid["build_evidence"] = {
            "artifacts": [
                {
                    "path": "/another-machine/build/firmware.elf",
                    "size_bytes": 0,
                    "sha256": "not-a-sha",
                }
            ]
        }
        errors = MODULE.validate_ir(invalid)
        self.assertTrue(any("path must be project-relative" in error for error in errors))
        self.assertTrue(any("size_bytes" in error for error in errors))
        self.assertTrue(any("sha256" in error for error in errors))

    def test_unknown_source_reference_is_invalid(self) -> None:
        invalid = ready_v2()
        invalid["camera"]["video_profiles"][0]["source_refs"] = [
            "missing-source"
        ]
        errors = MODULE.validate_ir(invalid)
        self.assertTrue(any("unknown source" in error for error in errors))

    def test_source_validation_rejects_invented_observation_scheme(self) -> None:
        invalid = ready_v2()
        invalid["sources"][0]["location"] = "intake-observed://missing.pdf"
        errors = MODULE.validate_source_locations(invalid, SCRIPT.parent)
        self.assertTrue(any("unsupported source scheme" in error for error in errors))

    def test_source_validation_resolves_and_hashes_local_file(self) -> None:
        valid = ready_v2()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence.pdf"
            evidence.write_bytes(b"evidence")
            valid["sources"][0]["location"] = "evidence.pdf"
            valid["sources"][0]["sha256"] = MODULE.sha256_file(evidence)
            self.assertEqual([], MODULE.validate_source_locations(valid, root))
            valid["sources"][0]["sha256"] = "0" * 64
            errors = MODULE.validate_source_locations(valid, root)
            self.assertTrue(any("does not match" in error for error in errors))

    def test_source_validation_rejects_machine_absolute_path(self) -> None:
        invalid = ready_v2()
        invalid["sources"][0]["location"] = "/another-machine/docs/board.pdf"
        errors = MODULE.validate_source_locations(invalid, SCRIPT.parent)
        self.assertTrue(any("must be IR-relative" in error for error in errors))


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
        self.assertEqual(
            "NEEDS_CONFIRMATION", assessment["features"]["ai_talk"]["status"]
        )
        for feature in ("h5_live_audio", "h5_live_video", "h5_talkback"):
            self.assertEqual("READY_TO_PORT", assessment["features"][feature]["status"])

    def test_mismatched_tirtc_platform_blocks_project(self) -> None:
        invalid_target = copy.deepcopy(self.ir)
        invalid_target["board"]["hardware_revision"] = "A"
        invalid_target["toolchain"]["verification"] = "corroborated"
        invalid_target["toolchain"]["tirtc"]["platform"] = "espressif-esp32p4"
        assessment = MODULE.assess_ir(invalid_target)
        self.assertEqual("BLOCKED", assessment["project_gate"]["status"])

    def test_esp32p4_accepts_only_matching_sdk_platform(self) -> None:
        ready = ready_v2()
        ready["soc"]["target"] = "esp32p4"
        ready["soc"]["module"] = "ESP32-P4"
        ready["toolchain"]["tirtc"]["platform"] = "espressif-esp32p4"
        assessment = MODULE.assess_ir(ready)
        self.assertEqual("READY_TO_PORT", assessment["project_gate"]["status"])


if __name__ == "__main__":
    unittest.main()

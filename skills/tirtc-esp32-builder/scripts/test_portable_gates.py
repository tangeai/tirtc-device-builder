from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audio_contract import verify_contract  # noqa: E402
from hardware_ir import artifact_requirement, constrain_project_gate  # noqa: E402
from install_audio_gate import MARKER, install  # noqa: E402
from install_video_gate import MARKER as VIDEO_MARKER  # noqa: E402
from install_video_gate import install as install_video  # noqa: E402
from project_portability import check_project  # noqa: E402
from video_contract import verify_contract as verify_video_contract  # noqa: E402


class PortableGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        for component in ("espressif__es7210", "espressif__es8311"):
            directory = self.project / "managed_components" / component
            directory.mkdir(parents=True)
            source = directory / component.split("__", 1)[1].replace("es7210", "es7210.c").replace("es8311", "es8311.c")
            source.write_text(
                "static const int coeff[][3] = {\n"
                "  {4096000, 8000, 1},\n"
                "  {12288000, 48000, 1},\n"
                "};\n",
                encoding="utf-8",
            )
        adapter = self.project / "components" / "starter_media" / "src"
        adapter.mkdir(parents=True)
        (adapter / "starter_media.c").write_text(
            """
#define AUDIO_SAMPLE_RATE_HZ 8000U
#define AUDIO_MCLK_MULTIPLE 512U
#define I2S_CAPTURE_PORT I2S_NUM_0
#define I2S_PLAYBACK_PORT I2S_NUM_1
#define ES7210_MIC1_TDM_INDEX 0U
static int config = I2S_TDM_SLOT0 | I2S_TDM_SLOT1 | I2S_TDM_SLOT2 | I2S_TDM_SLOT3;
static int codec = 0; /* .flags.tdm_enable = true */
void gate(void) { i2s_channel_reconfig_tdm_gpio(); i2s_channel_reconfig_std_gpio(); }
""",
            encoding="utf-8",
        )
        (self.project / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\nproject(test_project)\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def contract(self) -> dict:
        return {
            "schema_version": 1,
            "evidence": ["schematic", "codec-datasheet"],
            "clock": {
                "sample_rate_hz": 8000,
                "mclk_ratio": 512,
                "mclk_hz": 4096000,
                "codec_tables": [
                    {
                        "codec": "ES7210",
                        "source": "managed_components/espressif__es7210/es7210.c",
                    },
                    {
                        "codec": "ES8311",
                        "source": "managed_components/espressif__es8311/es8311.c",
                    },
                ],
            },
            "capture": {
                "controller": 0,
                "role": "master",
                "mode": "tdm",
                "tdm_enabled": True,
                "slot_count": 4,
                "slot_order": ["CH1", "CH3", "CH2", "CH4"],
                "slot_signals": ["MIC1", "REFERENCE", "MIC2", "GROUND"],
                "selected_slot": 0,
                "selected_signal": "MIC1",
                "mapping_evidence": "datasheet plus schematic",
            },
            "playback": {"controller": 1, "role": "master", "mode": "standard"},
            "shared_clock": {
                "gpios": [38, 14, 13],
                "directions_simultaneous": False,
                "handoff": "release_before_claim",
            },
            "implementation_assertions": [
                {
                    "file": "components/starter_media/src/starter_media.c",
                    "contains": [],
                    "contains_compact": [
                        "#defineAUDIO_MCLK_MULTIPLE512U",
                        ".flags.tdm_enable=true",
                        "#defineES7210_MIC1_TDM_INDEX0U",
                    ],
                    "absent": [],
                    "absent_compact": [".flags.tdm_enable=false"],
                }
            ],
        }

    def write_contract(self, contract: dict) -> Path:
        path = self.project / "board-audio-contract.json"
        path.write_text(json.dumps(contract), encoding="utf-8")
        return path

    def video_contract(self) -> dict:
        return {
            "schema_version": 1,
            "evidence": ["schematic", "locked-camera-source"],
            "dependencies": {
                "espressif/esp32-camera": "2.1.7",
                "idf": "5.5.4",
            },
            "scheduler": {
                "wifi_core": 0,
                "camera_core": 1,
                "config_files": ["sdkconfig.defaults", "sdkconfig"],
                "wifi_config_files": ["sdkconfig"],
            },
            "camera": {
                "codec": "mjpeg",
                "stream_id": 11,
                "media": "TIRTC_VIDEO_JPEG",
                "complete_jpeg_per_send": True,
                "frame_buffers": 2,
                "accepted_sensor_pids": [155, 8517],
                "unknown_sensor_policy": "reject",
            },
            "memory": {
                "max_send_buffer_bytes": 262144,
                "max_complete_jpeg_bytes": 196608,
                "video_backpressure_bytes": 196608,
            },
            "implementation_assertions": [
                {
                    "file": "main/app_main.c",
                    "contains": ["video_backpressure"],
                    "contains_compact": ["max_send_buffer=256*1024"],
                    "absent": [],
                    "absent_compact": ["max_send_buffer=1024*1024"],
                }
            ],
        }

    def write_video_fixture(self) -> Path:
        (self.project / "dependencies.lock").write_text(
            "dependencies:\n"
            "  espressif/esp32-camera:\n"
            "    version: 2.1.7\n"
            "  idf:\n"
            "    version: 5.5.4\n",
            encoding="utf-8",
        )
        camera_config = "# CONFIG_CAMERA_CORE0 is not set\nCONFIG_CAMERA_CORE1=y\n"
        (self.project / "sdkconfig.defaults").write_text(camera_config, encoding="utf-8")
        (self.project / "sdkconfig").write_text(
            camera_config + "CONFIG_ESP_WIFI_TASK_PINNED_TO_CORE_0=y\n",
            encoding="utf-8",
        )
        main = self.project / "main"
        main.mkdir(exist_ok=True)
        (main / "app_main.c").write_text(
            "int max_send_buffer = 256 * 1024; /* video_backpressure */\n",
            encoding="utf-8",
        )
        path = self.project / "board-video-contract.json"
        path.write_text(json.dumps(self.video_contract()), encoding="utf-8")
        return path

    def write_portable_sdk_inputs(self) -> None:
        (self.project / "dependencies.lock").write_text("dependencies: {}\n", encoding="utf-8")
        sdk = self.project / "third_party" / "tirtc"
        for relative in (
            "include/tirtc/tiRTC.h",
            "lib/libTiRTC.a",
            "manifest/build-contract.env",
        ):
            path = sdk / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"portable fixture\n")

    def test_supported_contract_passes(self) -> None:
        result = verify_contract(self.write_contract(self.contract()), self.project)
        self.assertTrue(result["ok"], result["errors"])

    def test_unsupported_clock_fails(self) -> None:
        contract = self.contract()
        contract["clock"].update({"mclk_ratio": 256, "mclk_hz": 2048000})
        result = verify_contract(self.write_contract(contract), self.project)
        self.assertFalse(result["ok"])
        self.assertTrue(any("rejects selected clock tuple" in item for item in result["errors"]))

    def test_inconsistent_topology_fails(self) -> None:
        contract = self.contract()
        contract["playback"]["controller"] = 0
        result = verify_contract(self.write_contract(contract), self.project)
        self.assertFalse(result["ok"])
        self.assertTrue(any("one I2S controller" in item for item in result["errors"]))

    def test_project_gate_follows_feature_block(self) -> None:
        project_gate = {"status": "BUILD_VERIFIED", "reasons": []}
        constrain_project_gate(
            project_gate,
            {"h5_live_audio": {"status": "BLOCKED", "reasons": []}},
        )
        self.assertEqual(project_gate["status"], "BLOCKED")

    def test_project_block_is_not_downgraded_by_unresolved_feature(self) -> None:
        project_gate = {"status": "BLOCKED", "reasons": ["platform mismatch"]}
        constrain_project_gate(
            project_gate,
            {
                "h5_live_audio": {
                    "status": "NEEDS_CONFIRMATION",
                    "reasons": [],
                }
            },
        )
        self.assertEqual(project_gate["status"], "BLOCKED")

    def test_build_artifact_must_exist_in_ir_evidence(self) -> None:
        recorded = "a" * 64
        unrecorded = "b" * 64
        data = {
            "build_evidence": {
                "artifacts": [
                    {
                        "path": "build/firmware.elf",
                        "size_bytes": 123,
                        "sha256": recorded,
                    }
                ]
            }
        }
        self.assertEqual(artifact_requirement(data, recorded)[0], "SATISFIED")
        requirement = artifact_requirement(data, unrecorded)
        self.assertEqual(requirement[0], "BLOCKED")
        self.assertIn("not present", requirement[1])

    def test_gate_installer_is_idempotent(self) -> None:
        self.write_contract(self.contract())
        install(self.project)
        install(self.project)
        cmake = (self.project / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertEqual(cmake.count(MARKER), 1)
        self.assertTrue((self.project / "tools" / "verify_audio_contract.py").is_file())

    def test_supported_video_contract_passes(self) -> None:
        result = verify_video_contract(self.write_video_fixture(), self.project)
        self.assertTrue(result["ok"], result["errors"])

    def test_supported_annex_b_contracts_pass(self) -> None:
        for codec, media in (
            ("h264", "TIRTC_VIDEO_H264"),
            ("h265", "TIRTC_VIDEO_H265"),
        ):
            with self.subTest(codec=codec):
                path = self.write_video_fixture()
                contract = self.video_contract()
                contract["camera"].update(
                    {
                        "codec": codec,
                        "media": media,
                        "complete_access_unit_per_send": True,
                    }
                )
                contract["camera"].pop("complete_jpeg_per_send")
                contract["memory"]["max_complete_access_unit_bytes"] = (
                    contract["memory"].pop("max_complete_jpeg_bytes")
                )
                path.write_text(json.dumps(contract), encoding="utf-8")
                result = verify_video_contract(path, self.project)
                self.assertTrue(result["ok"], result["errors"])

    def test_video_contract_rejects_camera_on_wifi_core(self) -> None:
        path = self.write_video_fixture()
        contract = self.video_contract()
        contract["scheduler"]["camera_core"] = 0
        path.write_text(json.dumps(contract), encoding="utf-8")
        result = verify_video_contract(path, self.project)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Wi-Fi core" in item for item in result["errors"]))

    def test_video_contract_rejects_oversized_backpressure(self) -> None:
        path = self.write_video_fixture()
        contract = self.video_contract()
        contract["memory"]["video_backpressure_bytes"] = 262144
        path.write_text(json.dumps(contract), encoding="utf-8")
        result = verify_video_contract(path, self.project)
        self.assertFalse(result["ok"])
        self.assertTrue(any("lower than max send buffer" in item for item in result["errors"]))

    def test_video_contract_rejects_unknown_sensor_fallback(self) -> None:
        path = self.write_video_fixture()
        contract = self.video_contract()
        contract["camera"]["unknown_sensor_policy"] = "accept"
        path.write_text(json.dumps(contract), encoding="utf-8")
        result = verify_video_contract(path, self.project)
        self.assertFalse(result["ok"])
        self.assertTrue(any("unknown_sensor_policy" in item for item in result["errors"]))

    def test_video_contract_rejects_stale_camera_lock(self) -> None:
        path = self.write_video_fixture()
        contract = self.video_contract()
        contract["dependencies"]["espressif/esp32-camera"] = "2.1.4"
        path.write_text(json.dumps(contract), encoding="utf-8")
        result = verify_video_contract(path, self.project)
        self.assertFalse(result["ok"])
        self.assertTrue(any("locked dependency mismatch" in item for item in result["errors"]))

    def test_video_gate_installer_is_idempotent(self) -> None:
        self.write_video_fixture()
        install_video(self.project)
        install_video(self.project)
        cmake = (self.project / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertEqual(cmake.count(VIDEO_MARKER), 1)
        self.assertTrue((self.project / "tools" / "verify_video_contract.py").is_file())

    def test_source_export_is_portable(self) -> None:
        self.write_portable_sdk_inputs()
        (self.project / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\n"
            "project(test_project)\n"
            "add_custom_target(gate COMMAND bash tools/gate.sh)\n",
            encoding="utf-8",
        )
        result = check_project(self.project, export=True)
        self.assertTrue(result["ok"], result["errors"])

    def test_source_export_rejects_cache_and_permission_dependent_gate(self) -> None:
        self.write_portable_sdk_inputs()
        (self.project / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\n"
            "project(test_project)\n"
            "add_custom_target(gate\n"
            "  COMMAND tools/gate.sh\n"
            ")\n",
            encoding="utf-8",
        )
        cache = self.project / "build" / "CMakeCache.txt"
        cache.parent.mkdir(parents=True)
        cache.write_text("CMAKE_HOME_DIRECTORY=/old/machine/project\n", encoding="utf-8")
        result = check_project(self.project, export=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("CMakeCache.txt" in item for item in result["errors"]))
        self.assertTrue(any("executable permission" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()

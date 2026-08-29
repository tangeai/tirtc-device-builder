from __future__ import annotations

import argparse
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("doctor.py")
SPEC = importlib.util.spec_from_file_location("doctor", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DoctorTest(unittest.TestCase):
    def create_workspace(self, root: Path) -> Path:
        thing_connect = root / "thing-connect"
        generator = thing_connect / MODULE.GENERATOR_RELATIVE_PATH
        generator.parent.mkdir(parents=True)
        generator.write_text("# test generator\n", encoding="utf-8")
        return thing_connect

    def create_sdk(self, root: Path) -> Path:
        sdk = root
        for relative in (
            Path("include/tirtc/tiRTC.h"),
            Path("lib/libTiRTC.a"),
            Path("manifest/build-contract.env"),
        ):
            path = sdk / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test\n", encoding="utf-8")
        return sdk

    def write_kit_manifest(self, root: Path, version: str) -> None:
        (root / MODULE.DEVICE_KIT_MANIFEST).write_text(
            '{"kit_version": "' + version + '"}\n', encoding="utf-8"
        )

    def diagnose_args(self, root: Path, idf_py: Path, expected_kit: str):
        return argparse.Namespace(
            expected_idf="5.5",
            expected_kit=expected_kit,
            target="esp32s3",
            idf_py=idf_py,
            thing_connect_root=root,
            require_workspace=True,
            sdk_dir=None,
            project=None,
            serial_port=None,
            json=False,
        )

    def test_version_matching_accepts_major_minor_line(self) -> None:
        self.assertTrue(MODULE.version_matches((5, 5, 2), "5.5"))
        self.assertTrue(MODULE.version_matches((5, 5, 2), "5.5.x"))
        self.assertFalse(MODULE.version_matches((5, 4, 4), "5.5"))

    def test_parse_idf_version(self) -> None:
        self.assertEqual((5, 5, 1), MODULE.parse_version("ESP-IDF v5.5.1"))
        self.assertEqual((5, 5), MODULE.parse_version("v5.5"))
        self.assertIsNone(MODULE.parse_version("unknown"))

    def test_contract_comparison_accepts_explicit_unset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = root / "build-contract.env"
            config = root / "sdkconfig.defaults"
            contract.write_text(
                "CONFIG_FREERTOS_HZ=1000\n"
                "CONFIG_FREERTOS_USE_TRACE_FACILITY=off\n"
                "CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS=off\n"
                "CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS=off\n",
                encoding="utf-8",
            )
            config.write_text(
                "CONFIG_FREERTOS_HZ=1000\n"
                "# CONFIG_FREERTOS_USE_TRACE_FACILITY is not set\n"
                "# CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS is not set\n"
                "# CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS is not set\n",
                encoding="utf-8",
            )
            self.assertEqual(
                [],
                MODULE.compare_contract(
                    MODULE.parse_env_file(contract), MODULE.parse_kconfig(config)
                ),
            )

    def test_contract_comparison_reports_mismatch(self) -> None:
        contract = {key: "off" for key in MODULE.CONTRACT_KEYS}
        contract["CONFIG_FREERTOS_HZ"] = "1000"
        config = dict(contract)
        config["CONFIG_FREERTOS_HZ"] = "100"
        mismatches = MODULE.compare_contract(contract, config)
        self.assertEqual(
            ["CONFIG_FREERTOS_HZ: expected 1000, got 100"], mismatches
        )

    def test_contract_comparison_accepts_hidden_disabled_child_boolean(self) -> None:
        contract = {key: "off" for key in MODULE.CONTRACT_KEYS}
        contract["CONFIG_FREERTOS_HZ"] = "1000"
        config = {
            "CONFIG_FREERTOS_HZ": "1000",
            "CONFIG_FREERTOS_USE_TRACE_FACILITY": "off",
            "CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS": "off",
        }
        self.assertEqual([], MODULE.compare_contract(contract, config))

    def test_contract_comparison_rejects_missing_required_scalar(self) -> None:
        contract = {key: "off" for key in MODULE.CONTRACT_KEYS}
        contract["CONFIG_FREERTOS_HZ"] = "1000"
        mismatches = MODULE.compare_contract(contract, {})
        self.assertIn(
            "project does not configure required CONFIG_FREERTOS_HZ=1000",
            mismatches,
        )

    def test_contract_comparison_rejects_expected_on_when_missing(self) -> None:
        contract = {key: "off" for key in MODULE.CONTRACT_KEYS}
        contract["CONFIG_FREERTOS_HZ"] = "1000"
        contract["CONFIG_FREERTOS_USE_TRACE_FACILITY"] = "on"
        mismatches = MODULE.compare_contract(
            contract, {"CONFIG_FREERTOS_HZ": "1000"}
        )
        self.assertIn(
            "project does not configure required "
            "CONFIG_FREERTOS_USE_TRACE_FACILITY=on",
            mismatches,
        )

    def test_workspace_accepts_repository_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            thing_connect = self.create_workspace(repository)
            self.assertEqual(
                thing_connect.resolve(),
                MODULE.normalize_thing_connect_root(repository),
            )

    def test_workspace_uses_environment_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            thing_connect = self.create_workspace(repository)
            with patch.dict(
                "os.environ",
                {MODULE.THING_CONNECT_ENV: str(repository)},
                clear=False,
            ):
                actual, source = MODULE.find_thing_connect_root(None, None)
            self.assertEqual(thing_connect.resolve(), actual)
            self.assertEqual(MODULE.THING_CONNECT_ENV, source)

    def test_device_kit_identity_reads_exact_manifest_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_kit_manifest(root, "1.1.1")
            identity = MODULE.inspect_device_kit(root)
            self.assertTrue(identity["manifest_present"])
            self.assertEqual("1.1.1", identity["version"])
            self.assertIsNone(identity["error"])

    def test_device_kit_identity_rejects_missing_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / MODULE.DEVICE_KIT_MANIFEST).write_text(
                "{}\n", encoding="utf-8"
            )
            identity = MODULE.inspect_device_kit(root)
            self.assertTrue(identity["manifest_present"])
            self.assertIsNone(identity["version"])
            self.assertIn("does not declare kit_version", str(identity["error"]))

    def test_doctor_rejects_structurally_complete_older_kit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self.create_workspace(root)
            self.create_sdk(workspace / MODULE.DEFAULT_SDK_RELATIVE_PATH)
            self.write_kit_manifest(workspace, "1.0.0")
            idf_py = root / "idf.py"
            idf_py.write_text("# test\n", encoding="utf-8")
            args = self.diagnose_args(workspace, idf_py, "1.1.1")
            with (
                patch.object(MODULE, "run_version", return_value=(0, "ESP-IDF v5.5.4")),
                patch.object(MODULE.shutil, "which", return_value="/test/tool"),
                patch.object(MODULE, "discover_serial_ports", return_value=[]),
            ):
                result = MODULE.diagnose(args)

            kit_check = next(
                item for item in result["checks"]
                if item["name"] == "ESP32 Device Kit"
            )
            self.assertEqual("FAIL", kit_check["status"])
            self.assertIn("version 1.0.0", kit_check["detail"])
            self.assertIn("expected 1.1.1", kit_check["detail"])
            self.assertEqual("FAIL", result["overall"])

    def test_doctor_accepts_exact_managed_kit_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = self.create_workspace(root)
            self.create_sdk(workspace / MODULE.DEFAULT_SDK_RELATIVE_PATH)
            self.write_kit_manifest(workspace, "1.1.1")
            idf_py = root / "idf.py"
            idf_py.write_text("# test\n", encoding="utf-8")
            args = self.diagnose_args(workspace, idf_py, "1.1.1")
            with (
                patch.object(MODULE, "run_version", return_value=(0, "ESP-IDF v5.5.4")),
                patch.object(MODULE.shutil, "which", return_value="/test/tool"),
                patch.object(MODULE, "discover_serial_ports", return_value=[]),
            ):
                result = MODULE.diagnose(args)

            kit_check = next(
                item for item in result["checks"]
                if item["name"] == "ESP32 Device Kit"
            )
            self.assertEqual("PASS", kit_check["status"])
            self.assertIn("version 1.1.1", kit_check["detail"])
            self.assertEqual("PASS", result["overall"])

    def test_project_bundled_sdk_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            bundled = self.create_sdk(project / "third_party" / "tirtc")
            workspace = self.create_workspace(root / "repository")
            actual, source = MODULE.resolve_sdk_dir(None, project, workspace)
            self.assertEqual(bundled.resolve(), actual)
            self.assertEqual("generated project", source)

    def test_explicit_sdk_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            explicit = root / "explicit-sdk"
            project = root / "project"
            self.create_sdk(project / "third_party" / "tirtc")
            actual, source = MODULE.resolve_sdk_dir(explicit, project, None)
            self.assertEqual(explicit.resolve(), actual)
            self.assertEqual("explicit --sdk-dir", source)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("doctor.py")
SPEC = importlib.util.spec_from_file_location("bk_doctor", MODULE_PATH)
assert SPEC and SPEC.loader
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class DoctorTests(unittest.TestCase):
    def test_missing_root_needs_setup(self) -> None:
        self.assertEqual("NEEDS_SETUP", doctor.inspect(None)["overall"])

    def test_sdk_shape_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in doctor.REQUIRED_SDK_PATHS:
                path = root / relative
                if "." in path.name:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("test\n", encoding="utf-8")
                else:
                    path.mkdir(parents=True, exist_ok=True)
            result = doctor.inspect(root)
            self.assertTrue(all(item["status"] == "PASS" for item in result["checks"] if item["name"].startswith("sdk:")))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("create_esp32_project.py")
SPEC = importlib.util.spec_from_file_location("create_esp32_project", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def c_function_body(text: str, name: str) -> str:
    marker = f"{name}("
    start = text.index(marker)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace : index + 1]
    raise AssertionError(f"unterminated C function: {name}")


class CreateEsp32ProjectTest(unittest.TestCase):
    def test_rejects_unsafe_project_name(self) -> None:
        for name in ("BadName", "../escape", "has-dash", "", "1device"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                MODULE.validate_project_name(name)

    def test_generates_focused_self_contained_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "camera_device"
            _, _, sdk = MODULE.repository_paths()
            MODULE.create_project(output, "camera_device", sdk)

            self.assertTrue((output / "CMakeLists.txt").is_file())
            self.assertTrue((output / "third_party/tirtc/lib/libTiRTC.a").is_file())
            self.assertTrue((output / "platform-media-contract.json").is_file())
            self.assertTrue((output / "tirtc-runtime-contract.json").is_file())
            self.assertFalse((output / "media").exists())
            self.assertTrue((output / "components/starter_runtime").is_dir())
            self.assertFalse((output / "components/session_runtime").exists())
            self.assertFalse((output / "components/device_core").exists())
            self.assertFalse((output / "components/starter_media_file").exists())

            platform_header = (
                output / "components/platform_client/include/platform_client.h"
            ).read_text(encoding="utf-8")
            platform_source = (
                output / "components/platform_client/src/platform_client.c"
            ).read_text(encoding="utf-8")
            self.assertNotIn("PLATFORM_SERVICE_VOIP", platform_header)
            self.assertNotIn("PLATFORM_SERVICE_CALL", platform_header)
            self.assertNotIn('"voip-srv"', platform_source)
            self.assertNotIn('"call-srv"', platform_source)
            self.assertIn('"tirtc-srv"', platform_source)
            self.assertIn("platform_client_tirtc_endpoint", platform_header)

            app_main = (output / "main/app_main.c").read_text(encoding="utf-8")
            tirtc_source = (
                output / "components/starter_tirtc/src/starter_tirtc.c"
            ).read_text(encoding="utf-8")
            runtime_source = (
                output / "components/starter_runtime/src/starter_runtime.c"
            ).read_text(encoding="utf-8")
            self.assertIn(".service_endpoint = tirtc_endpoint", app_main)
            self.assertIn("TIRTC_OPT_SERVICE_ENDPOINT", tirtc_source)
            self.assertIn("TIRTC_VIDEO_JPEG", tirtc_source)
            self.assertIn("TIRTC_VIDEO_H264", tirtc_source)
            self.assertIn("TIRTC_VIDEO_H265", tirtc_source)
            self.assertIn("frame->media != TIRTC_AUDIO_ALAW", tirtc_source)
            self.assertIn("frame->flags != TIRTC_AUDIOSAMPLE_8K16B1C", tirtc_source)
            for callback in ("on_conn_accepted", "on_ai_connect"):
                self.assertNotIn("TiRtcDisconnect", c_function_body(tirtc_source, callback))
            for response_field in ('"session_id"', '"input_audio"', '"output_audio"'):
                self.assertIn(response_field, runtime_source)
            self.assertIn("ai_audio_format_is_alaw_8k_mono", runtime_source)
            self.assertIn('strcmp(method->valuestring, "end_session")', runtime_source)

            cmake = (output / "CMakeLists.txt").read_text(encoding="utf-8")
            readme = (output / "README.md").read_text(encoding="utf-8")
            self.assertIn("project(camera_device)", cmake)
            self.assertNotIn("spiffs_create_partition_image", cmake)
            self.assertNotIn("audio.g711a", readme)
            self.assertNotIn("video.h264", readme)
            self.assertNotIn("@PROJECT_NAME@", readme)
            self.assertNotIn("VoIP", readme)
            self.assertNotIn("设备互呼", readme)

            wifi_source = (
                output / "components/wifi_manager/src/wifi_manager.c"
            ).read_text(encoding="utf-8")
            self.assertIn('"TiRTC-%02X%02X"', wifi_source)
            self.assertIn("ap.ap.authmode = WIFI_AUTH_OPEN", wifi_source)
            self.assertIn(
                "esp_netif_set_ip4_addr(&ip_info.ip, WIFI_SETUP_IP_A,",
                wifi_source,
            )
            self.assertIn('"http://192.168.6.1"', wifi_source)
            self.assertIn("httpd_register_err_handler", wifi_source)
            self.assertIn("wifi_captive_dns_start", wifi_source)
            self.assertNotIn("ESP_NETIF_CAPTIVEPORTAL_URI", wifi_source)
            self.assertNotIn("WIFI_SETUP_PASSWORD", wifi_source)
            self.assertNotIn("TiRTC-Setup-", wifi_source)
            self.assertNotIn("192.168.4.1", wifi_source)

            dns_source = (
                output / "components/wifi_manager/src/wifi_captive_dns.c"
            ).read_text(encoding="utf-8")
            wifi_cmake = (
                output / "components/wifi_manager/CMakeLists.txt"
            ).read_text(encoding="utf-8")
            self.assertIn("wildcard DNS listening", dns_source)
            self.assertIn("DNS_FLAG_RESPONSE", dns_source)
            self.assertIn('"src/wifi_captive_dns.c"', wifi_cmake)
            self.assertIn("lwip", wifi_cmake)

    def test_does_not_overwrite_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "existing"
            output.mkdir()
            _, _, sdk = MODULE.repository_paths()
            with self.assertRaises(FileExistsError):
                MODULE.create_project(output, "existing", sdk)

    def test_h5_contract_separates_platform_and_board_codec_capability(self) -> None:
        h5_contract = (SCRIPT.parents[2] / "device-h5-live.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("平台和 Web 播放端支持 `MJPEG`、`H.264`、`H.265`", h5_contract)
        self.assertIn("具体设备必须根据硬件和驱动证据选定一种", h5_contract)
        self.assertIn("一张完整 JPEG", h5_contract)


if __name__ == "__main__":
    unittest.main()

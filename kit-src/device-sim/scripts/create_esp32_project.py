#!/usr/bin/env python3
"""Generate a focused ESP32-S3 or ESP32-P4 ThingConnect project."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


PROJECT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
TEXT_SUFFIXES = {"", ".c", ".h", ".md", ".txt", ".json", ".csv"}
SHARED_COMPONENTS = (
    "platform_client",
    "runtime_config",
    "wifi_manager",
)
TARGETS = ("esp32s3", "esp32p4")
SDK_DIRS = {
    "esp32s3": ("espressif-esp32s3", "2.5.0"),
    "esp32p4": ("espressif-esp32p4", "2.5.0"),
}
P4_PROJECT_NAME = "xiaotai_esp32p4"
P4_COPY_IGNORES = (
    "build",
    "managed_components",
    "sdkconfig",
    "sdkconfig.old",
    "__pycache__",
    "*.pyc",
    ".git",
    ".gitignore",
    ".gitattributes",
)


def replace_exact(text: str, old: str, new: str, description: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"cannot focus platform component: {description}")
    return text.replace(old, new)


def focus_platform_component(component: Path) -> None:
    """Narrow the shared transport to the services exposed by this starter."""
    header_path = component / "include" / "platform_client.h"
    header = header_path.read_text(encoding="utf-8")
    header = replace_exact(
        header,
        """typedef enum {
    PLATFORM_SERVICE_DEVICE = 0,
    PLATFORM_SERVICE_VOIP,
    PLATFORM_SERVICE_AI,
    PLATFORM_SERVICE_CALL,
} platform_service_t;
""",
        """typedef enum {
    PLATFORM_SERVICE_DEVICE = 0,
    PLATFORM_SERVICE_AI,
} platform_service_t;
""",
        "platform service enum changed",
    )
    header_path.write_text(header, encoding="utf-8")

    source_path = component / "src" / "platform_client.c"
    source = source_path.read_text(encoding="utf-8")
    source = replace_exact(
        source,
        """typedef struct {
    char device[256];
    char voip[256];
    char ai[256];
    char call[256];
    char mqtt[256];
    char tirtc[256];
} platform_services_t;
""",
        """typedef struct {
    char device[256];
    char ai[256];
    char mqtt[256];
    char tirtc[256];
} platform_services_t;
""",
        "platform service storage changed",
    )
    source = replace_exact(
        source,
        """              json_copy_string(root, "device-srv", s_services.device,
                               sizeof(s_services.device)) &&
              json_copy_string(root, "voip-srv", s_services.voip,
                               sizeof(s_services.voip)) &&
              json_copy_string(root, "ai-srv", s_services.ai,
                               sizeof(s_services.ai)) &&
              json_copy_string(root, "call-srv", s_services.call,
                               sizeof(s_services.call)) &&
              json_copy_string(root, "mqtt-srv", s_services.mqtt,
""",
        """              json_copy_string(root, "device-srv", s_services.device,
                               sizeof(s_services.device)) &&
              json_copy_string(root, "ai-srv", s_services.ai,
                               sizeof(s_services.ai)) &&
              json_copy_string(root, "mqtt-srv", s_services.mqtt,
""",
        "service discovery parser changed",
    )
    source = replace_exact(
        source,
        """    case PLATFORM_SERVICE_DEVICE: return s_services.device;
    case PLATFORM_SERVICE_VOIP: return s_services.voip;
    case PLATFORM_SERVICE_AI: return s_services.ai;
    case PLATFORM_SERVICE_CALL: return s_services.call;
""",
        """    case PLATFORM_SERVICE_DEVICE: return s_services.device;
    case PLATFORM_SERVICE_AI: return s_services.ai;
""",
        "service routing switch changed",
    )
    source_path.write_text(source, encoding="utf-8")


def repository_paths(target: str = "esp32s3") -> tuple[Path, Path, Path]:
    if target not in TARGETS:
        raise ValueError(f"unsupported target: {target}")
    device_sim = Path(__file__).resolve().parent.parent
    sdk = device_sim / "sdk" / Path(*SDK_DIRS[target])
    reference_components = device_sim / "device-sim-esp32" / "components"
    if target == "esp32p4":
        template = device_sim / "device-sim-p4"
    else:
        template = device_sim / "templates" / "esp32-h5-ai"
    return template, reference_components, sdk


def validate_project_name(name: str) -> str:
    if not PROJECT_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "project name must start with a lowercase letter and contain only "
            "lowercase letters, digits, or underscores (maximum 32 characters)"
        )
    return name


def replace_placeholders(root: Path, project_name: str) -> None:
    replacements = {"@PROJECT_NAME@": project_name}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for placeholder, value in replacements.items():
            updated = updated.replace(placeholder, value)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def validate_sdk(sdk_source: Path) -> None:
    required_sdk_files = (
        sdk_source / "include" / "tirtc" / "tiRTC.h",
        sdk_source / "lib" / "libTiRTC.a",
        sdk_source / "manifest" / "build-contract.env",
    )
    missing = [str(path) for path in required_sdk_files if not path.is_file()]
    if missing:
        raise FileNotFoundError("incomplete TiRTC SDK: " + ", ".join(missing))


def create_s3_project(output: Path, project_name: str, sdk_source: Path) -> None:
    template, reference_components, _ = repository_paths("esp32s3")
    if not template.is_dir():
        raise FileNotFoundError(f"template resources are missing: {template}")
    shutil.copytree(template, output)
    for component in SHARED_COMPONENTS:
        shutil.copytree(
            reference_components / component,
            output / "components" / component,
        )
    focus_platform_component(output / "components" / "platform_client")
    shutil.copytree(sdk_source, output / "third_party" / "tirtc")
    replace_placeholders(output, project_name)


def create_p4_project(output: Path, project_name: str, sdk_source: Path) -> None:
    """Copy the full P4 reference (UI, hosted Wi-Fi, camera) as the project base.

    The reference intentionally keeps product naming; only the CMake project()
    call is renamed. Shared transport components are materialized under
    components/ so the generated project is self-contained and the reference's
    guarded EXTRA_COMPONENT_DIRS block self-skips.
    """
    template, reference_components, _ = repository_paths("esp32p4")
    if not template.is_dir():
        raise FileNotFoundError(f"P4 reference resources are missing: {template}")
    shutil.copytree(template, output, ignore=shutil.ignore_patterns(*P4_COPY_IGNORES))
    for component in SHARED_COMPONENTS:
        shutil.copytree(
            reference_components / component,
            output / "components" / component,
        )
    shutil.copytree(sdk_source, output / "third_party" / "tirtc")
    cmake_path = output / "CMakeLists.txt"
    cmake = cmake_path.read_text(encoding="utf-8")
    cmake = replace_exact(
        cmake,
        f"project({P4_PROJECT_NAME})",
        f"project({project_name})",
        "P4 project name changed",
    )
    cmake_path.write_text(cmake, encoding="utf-8")


def create_project(
    output: Path,
    project_name: str,
    sdk_source: Path | None,
    target: str = "esp32s3",
) -> None:
    if target not in TARGETS:
        raise ValueError(f"unsupported target: {target}")
    project_name = validate_project_name(project_name)
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"output path already exists: {output}")

    _, _, default_sdk = repository_paths(target)
    sdk_source = sdk_source.resolve() if sdk_source else default_sdk
    validate_sdk(sdk_source)

    try:
        if target == "esp32p4":
            create_p4_project(output, project_name, sdk_source)
        else:
            create_s3_project(output, project_name, sdk_source)
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an ESP32-S3 starter with device onboarding, H5 live/talkback, "
            "and AI talk (VoIP and device calling are intentionally excluded), or "
            "copy the full ESP32-P4 reference firmware for --target esp32p4."
        )
    )
    parser.add_argument("output", type=Path, help="new project directory")
    parser.add_argument(
        "--name",
        help="ESP-IDF project name; defaults to the output directory name",
    )
    parser.add_argument(
        "--target",
        choices=TARGETS,
        default="esp32s3",
        help="chip target; esp32p4 copies the full reference firmware",
    )
    parser.add_argument(
        "--sdk-dir",
        type=Path,
        default=None,
        help="TiRTC SDK directory copied into the generated project; "
             "defaults to the versioned kit SDK for the selected target",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_name = args.name or args.output.name.replace("-", "_")
    create_project(args.output, project_name, args.sdk_dir, args.target)
    print(f"created ESP32 project for {args.target}: {args.output.resolve()}")
    print("next:")
    print(f"  cd {args.output}")
    print(f"  idf.py set-target {args.target}")
    print("  idf.py build")


if __name__ == "__main__":
    main()

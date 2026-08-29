#!/usr/bin/env python3
"""Install the portable TiRTC runtime protocol gate into an ESP-IDF project."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


MARKER = "# tirtc-runtime-semantic-gate-v1"
BLOCK = f"""

{MARKER}
add_custom_target(tirtc_runtime_semantic_gate ALL
    COMMAND "${{PYTHON}}"
            "${{CMAKE_CURRENT_LIST_DIR}}/tools/verify_runtime_contract.py"
            "${{CMAKE_CURRENT_LIST_DIR}}/tirtc-runtime-contract.json"
            --project "${{CMAKE_CURRENT_LIST_DIR}}"
            --evidence-out "${{CMAKE_BINARY_DIR}}/runtime-contract-evidence.json"
    COMMENT "Validating TiRTC endpoint, callbacks, streams and AI media negotiation"
    VERBATIM
)
add_dependencies(${{CMAKE_PROJECT_NAME}}.elf tirtc_runtime_semantic_gate)
"""


def install(project: Path) -> None:
    project = project.expanduser().resolve()
    cmake = project / "CMakeLists.txt"
    contract = project / "tirtc-runtime-contract.json"
    if not cmake.is_file():
        raise ValueError(f"ESP-IDF project CMakeLists.txt not found: {cmake}")
    if not contract.is_file():
        raise ValueError(
            f"runtime contract not found: {contract}; create and verify it before installing the gate"
        )
    tools = project / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    destination = tools / "verify_runtime_contract.py"
    source = Path(__file__).resolve().with_name("runtime_contract.py")
    if destination.exists() and destination.read_bytes() != source.read_bytes():
        raise ValueError(f"refusing to overwrite a different gate: {destination}")
    if not destination.exists():
        shutil.copyfile(source, destination)
    text = cmake.read_text(encoding="utf-8")
    if MARKER not in text:
        cmake.write_text(text.rstrip() + BLOCK + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    try:
        install(args.project)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"installed TiRTC runtime semantic gate: {args.project.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

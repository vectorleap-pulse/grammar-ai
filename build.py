#!/usr/bin/env python3
"""Build script for Grammar AI using PyInstaller."""

import argparse
import platform
import subprocess
import sys
import tomllib
from pathlib import Path


def get_project_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as handle:
        project = tomllib.load(handle)
    return project["project"]["version"]


def normalize_arch(machine: str) -> str:
    arch = machine.lower().replace(" ", "-")
    if arch in {"amd64", "x86_64"}:
        return "x64"
    if arch in {"aarch64", "arm64"}:
        return "arm64"
    return arch or "unknown"


def normalize_platform() -> str:
    system = platform.system().lower().replace(" ", "-")
    arch = normalize_arch(platform.machine())
    return f"{system}-{arch}"


def build_exe(debug: bool = False) -> int:
    """Build Grammar AI executable using PyInstaller."""
    root = Path(__file__).parent
    output_dir = root / "dist"
    build_dir = root / "build"
    spec_dir = build_dir
    output_dir.mkdir(exist_ok=True)
    build_dir.mkdir(exist_ok=True)

    version = get_project_version(root / "pyproject.toml")
    platform_tag = normalize_platform()
    binary_name = f"grammar-ai-{platform_tag}-v{version}"

    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name",
        binary_name,
        "--distpath",
        str(output_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(spec_dir),
        "--clean",
        "--noconfirm",
    ]

    if debug:
        pyinstaller_args.append("--console")
    else:
        pyinstaller_args.append("--windowed")

    pyinstaller_args.append("main.py")

    print("Building Grammar AI executable with PyInstaller...")
    print(
        f"Output file: {output_dir / (binary_name + ('.exe' if sys.platform.startswith('win') else ''))}"
    )
    print(f"Command: {' '.join(pyinstaller_args)}")

    result = subprocess.run(pyinstaller_args, cwd=root)
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Grammar AI executable")
    parser.add_argument(
        "--debug", action="store_true", help="Build with console window for debugging"
    )
    args = parser.parse_args()
    sys.exit(build_exe(debug=args.debug))

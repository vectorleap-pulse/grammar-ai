#!/usr/bin/env python3
"""Build script for Grammar AI using PyInstaller on Windows."""

import subprocess
import sys
from pathlib import Path


def build_windows_exe(debug: bool = False) -> int:
    """Build Grammar AI executable for Windows using PyInstaller."""
    output_dir = Path("dist")
    build_dir = Path("build")
    spec_dir = Path("build")
    output_dir.mkdir(exist_ok=True)
    build_dir.mkdir(exist_ok=True)

    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name",
        "main",
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
    print(f"Command: {' '.join(pyinstaller_args)}")

    result = subprocess.run(pyinstaller_args, cwd=Path(__file__).parent)
    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Grammar AI executable")
    parser.add_argument(
        "--debug", action="store_true", help="Build with console window for debugging"
    )
    args = parser.parse_args()
    sys.exit(build_windows_exe(debug=args.debug))

#!/usr/bin/env python3
"""Build script for Grammar AI using Nuitka on Windows."""

import subprocess
import sys
from pathlib import Path


def build_windows_exe() -> int:
    """Build Grammar AI executable for Windows using Nuitka."""
    output_dir = Path("dist")
    output_dir.mkdir(exist_ok=True)

    nuitka_args = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--windows-console-mode=disable",
        "--windows-icon-from-ico=app/ui/icon.ico" if Path("app/ui/icon.ico").exists() else "",
        "--include-package=app",
        "--include-data-files=app/**/*.py=app/",
        "--output-dir=dist",
        "--remove-output",
        "--follow-imports",
        "--enable-plugin=tk-inter",
        "main.py",
    ]

    # Filter out empty strings
    nuitka_args = [arg for arg in nuitka_args if arg]

    print("Building Grammar AI executable with Nuitka...")
    print(f"Command: {' '.join(nuitka_args)}")

    result = subprocess.run(nuitka_args, cwd=Path(__file__).parent)
    return result.returncode


if __name__ == "__main__":
    sys.exit(build_windows_exe())

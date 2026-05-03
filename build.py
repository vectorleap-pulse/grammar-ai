#!/usr/bin/env python3
"""Build script for Grammar AI using Nuitka on Windows."""

import subprocess
import sys
from pathlib import Path


def build_windows_exe(debug: bool = False) -> int:
    """Build Grammar AI executable for Windows using Nuitka."""
    output_dir = Path("dist")
    output_dir.mkdir(exist_ok=True)

    nuitka_args = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--assume-yes-for-downloads",
        "--include-package=app",
        "--output-dir=dist",
        "--remove-output",
        "--follow-imports",
        "--enable-plugin=tk-inter",
        "--show-progress",
        "main.py",
    ]

    if debug:
        nuitka_args.insert(-1, "--windows-console-mode=force")
    else:
        nuitka_args.insert(-1, "--windows-disable-console")

    # Filter out empty strings
    nuitka_args = [arg for arg in nuitka_args if arg]

    print("Building Grammar AI executable with Nuitka...")
    print(f"Command: {' '.join(nuitka_args)}")

    result = subprocess.run(nuitka_args, cwd=Path(__file__).parent)
    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Grammar AI executable")
    parser.add_argument(
        "--debug", action="store_true", help="Build with console window for debugging"
    )
    args = parser.parse_args()
    sys.exit(build_windows_exe(debug=args.debug))

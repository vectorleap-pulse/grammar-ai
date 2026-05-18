#!/usr/bin/env python3
"""Build script for Grammar AI using Nuitka (standalone mode)."""

import argparse
import os
import subprocess
import sys
import tomllib
from pathlib import Path


def get_project_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as handle:
        project = tomllib.load(handle)
    return project["project"]["version"]


def _make_ico(png_path: Path, ico_path: Path) -> None:
    """Convert PNG to a multi-resolution ICO using Pillow."""
    from PIL import Image

    img = Image.open(png_path).convert("RGBA")
    img.save(
        ico_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )


def build_exe(debug: bool = False) -> int:
    """Build Grammar AI as a Nuitka standalone distribution."""
    root = Path(__file__).parent
    build_dir = root / "build"
    build_dir.mkdir(exist_ok=True)
    (root / "dist").mkdir(exist_ok=True)

    version = get_project_version(root / "pyproject.toml")
    standalone_dir = build_dir / "grammar-ai.dist"

    nuitka_args = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--lto=no",
        f"--jobs={os.cpu_count() or 1}",
        f"--output-dir={build_dir}",
        "--output-filename=grammar-ai.exe",
        "--enable-plugin=tk-inter",
        f"--include-data-files={root / 'pyproject.toml'}=pyproject.toml",
        f"--include-data-files={root / 'resources' / 'icon.png'}=resources/icon.png",
    ]

    if sys.platform.startswith("win"):
        ico_path = root / "resources" / "icon.ico"
        _make_ico(root / "resources" / "icon.png", ico_path)
        nuitka_args.append(f"--windows-icon-from-ico={ico_path}")
        if not debug:
            nuitka_args.append("--windows-disable-console")

    nuitka_args.append("main.py")

    print(f"Building Grammar AI v{version} with Nuitka (standalone)...")
    print(f"Standalone output: {standalone_dir}")
    print(f"Command: {' '.join(str(a) for a in nuitka_args)}")

    result = subprocess.run(nuitka_args, cwd=root)
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Grammar AI executable")
    parser.add_argument(
        "--debug", action="store_true", help="Build with console window for debugging"
    )
    args = parser.parse_args()
    sys.exit(build_exe(debug=args.debug))

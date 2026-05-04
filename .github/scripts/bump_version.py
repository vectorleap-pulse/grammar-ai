#!/usr/bin/env python3
"""Bump the project version in pyproject.toml and emit GitHub Actions output."""

import argparse
import os
import tomllib
from pathlib import Path
from typing import Sequence

import tomli_w


def parse_version(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Unsupported version format: {version!r}")
    return tuple(int(part) for part in parts)


def format_version(version_parts: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version_parts)


def bump_version(current_version: str, bump_type: str) -> str:
    major, minor, patch = parse_version(current_version)
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")
    return format_version((major, minor, patch))


def load_pyproject(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def save_pyproject(path: Path, data: dict) -> None:
    with path.open("wb") as handle:
        tomli_w.dump(data, handle)


def emit_github_output(name: str, value: str) -> None:
    github_output_path = os.environ.get("GITHUB_OUTPUT")
    if not github_output_path:
        return
    with open(github_output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bump pyproject.toml version")
    parser.add_argument("bump_type", choices=["patch", "minor", "major"])
    parser.add_argument(
        "--pyproject-path",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml",
    )
    args = parser.parse_args(argv)

    data = load_pyproject(args.pyproject_path)
    current_version = data["project"]["version"]
    new_version = bump_version(current_version, args.bump_type)
    data["project"]["version"] = new_version
    save_pyproject(args.pyproject_path, data)

    print(f"Version bumped from {current_version} to {new_version}")
    emit_github_output("new_version", new_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

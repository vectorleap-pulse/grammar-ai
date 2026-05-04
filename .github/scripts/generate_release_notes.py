#!/usr/bin/env python3
"""Generate release notes for GitHub Actions release creation."""

import argparse
import os
from pathlib import Path
from typing import Sequence

DEFAULT_NOTES = """## What's Changed

This release includes various improvements and bug fixes.

### Version
- Bumped to v{new_version}

### Build
- Built executable for Windows
"""


def build_release_notes(release_notes: str, new_version: str, template_path: Path) -> str:
    release_notes = release_notes or ""
    if not release_notes.strip() and template_path.exists():
        release_notes = template_path.read_text(encoding="utf-8")
    if not release_notes.strip():
        release_notes = DEFAULT_NOTES
    return release_notes.replace("{{version}}", f"v{new_version}")


def emit_github_output(name: str, value: str) -> None:
    github_output_path = os.environ.get("GITHUB_OUTPUT")
    if not github_output_path:
        raise RuntimeError("GITHUB_OUTPUT environment variable is not set")
    with open(github_output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}<<EOF\n")
        handle.write(value)
        if not value.endswith("\n"):
            handle.write("\n")
        handle.write("EOF\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate release notes for GitHub Actions")
    parser.add_argument("--new-version", required=True, help="New semantic version string")
    parser.add_argument(
        "--template-path",
        type=Path,
        default=Path("media/release-note-template.md"),
        help="Release note template path",
    )
    parser.add_argument(
        "--release-notes",
        default=os.environ.get("RELEASE_NOTES", ""),
        help="Release notes text",
    )
    args = parser.parse_args(argv)

    notes = build_release_notes(args.release_notes, args.new_version, args.template_path)
    emit_github_output("notes", notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

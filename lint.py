#!/usr/bin/env python3
"""Linter script that runs ruff and mypy checks."""

import subprocess
import sys


def run_linter():
    """Run ruff check and mypy on the project."""
    try:
        print("Running ruff format...")
        subprocess.run([sys.executable, "-m", "ruff", "format", "."], check=True)
        print("Ruff format passed.")
        print("Running ruff check...")
        subprocess.run([sys.executable, "-m", "ruff", "check", "--fix", "."], check=True)
        print("Ruff check passed.")
    except subprocess.CalledProcessError as e:
        print(f"Ruff check failed with exit code {e.returncode}")
        sys.exit(1)

    try:
        print("Running mypy...")
        subprocess.run([sys.executable, "-m", "mypy", "."], check=True)
        print("Mypy check passed.")
    except subprocess.CalledProcessError as e:
        print(f"Mypy check failed with exit code {e.returncode}")
        sys.exit(1)

    print("All linter checks passed!")


if __name__ == "__main__":
    run_linter()

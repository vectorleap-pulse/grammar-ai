from __future__ import annotations

import json
import urllib.request
from typing import Optional

from loguru import logger

from app.config import RELEASES_API


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except ValueError:
        return (0,)


def check_for_update(current_version: str) -> Optional[tuple[str, str]]:
    """Returns (new_version, release_page_url) if a newer release exists, otherwise None."""
    try:
        req = urllib.request.Request(
            RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "grammar-ai-updater",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        if data.get("draft") or data.get("prerelease"):
            return None

        latest = data.get("tag_name", "").lstrip("v")
        if not latest or _parse_version(latest) <= _parse_version(current_version):
            return None

        html_url = data.get("html_url", "")
        if html_url:
            return latest, html_url
    except Exception as e:
        logger.warning(f"Update check failed: {e}")
    return None

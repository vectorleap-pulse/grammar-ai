"""Update checking, downloading, and revealing - never silently self-executing.

Checks GitHub Releases for a newer version and, if found, downloads the installer to
the user's real Downloads folder. The downloaded installer is never executed by this
app - `open_containing_folder()` only opens Explorer with it selected. An unsigned
process that downloads an unsigned .exe and then executes it itself is close to the
textbook definition of dropper/stager behavior and gets flagged by AV/EDR heuristics
for exactly that reason (this codebase has already been burned once, by a different
pattern - see app/core/hotkey.py's docstring). Requiring a genuine human double-click
in Explorer to actually launch the installer is the same pattern every browser already
uses for downloaded files, and isn't flagged.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import NamedTuple, Optional

from loguru import logger

from app.config import RELEASES_API

_IS_WIN = sys.platform == "win32"

# FOLDERID_Downloads - not exposed as a plain path since the user may have relocated
# Downloads (Explorer's Properties > Location tab) or have OneDrive Known Folder Move
# redirecting it elsewhere, both common - Path.home() / "Downloads" would be wrong.
_FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"


class UpdateInfo(NamedTuple):
    version: str
    release_url: str
    download_url: str


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except ValueError:
        return (0,)


def check_for_update(current_version: str) -> Optional[UpdateInfo]:
    """Returns an UpdateInfo if a newer release (with an installer asset) exists."""
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
        if not html_url:
            return None

        download_url = ""
        for asset in data.get("assets") or []:
            name = asset.get("name", "")
            if name.endswith(".exe"):
                download_url = asset.get("browser_download_url", "")
                break

        if not download_url:
            logger.warning("Update check found a new release but no installer asset on it")
            return None

        return UpdateInfo(version=latest, release_url=html_url, download_url=download_url)
    except Exception as e:
        logger.warning(f"Update check failed: {e}")
    return None


def get_downloads_folder() -> Path:
    """Resolve the user's actual Downloads folder via the Windows Known Folder API.

    Not Path.home() / "Downloads" - see the FOLDERID_Downloads comment above.
    """
    if not _IS_WIN:
        return Path.home() / "Downloads"

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.wintypes.DWORD),
            ("Data2", ctypes.wintypes.WORD),
            ("Data3", ctypes.wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    guid = _GUID()
    ctypes.windll.ole32.CLSIDFromString(_FOLDERID_DOWNLOADS, ctypes.byref(guid))  # type: ignore[attr-defined]

    path_ptr = ctypes.c_wchar_p()
    shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(_GUID),
        ctypes.wintypes.DWORD,
        ctypes.wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    result = shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path_ptr))
    if result != 0 or not path_ptr.value:
        logger.warning(f"SHGetKnownFolderPath failed (hresult {result}), falling back")
        return Path.home() / "Downloads"

    try:
        return Path(path_ptr.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)  # type: ignore[attr-defined]


def download_installer(download_url: str, dest_dir: Path) -> Path:
    """Download the installer asset into dest_dir, returning its final path.

    Idempotent: if a file with the expected (already version-qualified) name already
    exists, the download is skipped entirely and that file is returned as-is - this
    covers both a repeated check within one session and a later session finding a
    file downloaded, but not yet installed, previously.

    Downloads to a temp path first and only os.replace()s it onto the final name once
    the stream completes without error, so a crash/kill mid-download never leaves a
    truncated file sitting at the path the idempotency check above looks for.
    """
    filename = download_url.rsplit("/", 1)[-1].split("?", 1)[0].split("#", 1)[0]
    dest_path = dest_dir / filename
    if dest_path.exists():
        tmp_path = dest_dir / f"{filename}.part"
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError as e:
                logger.debug(f"Could not remove stale temp download {tmp_path}: {e}")
        return dest_path

    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_dir / f"{filename}.part"
    if tmp_path.exists():
        try:
            tmp_path.unlink()
        except OSError as e:
            logger.debug(f"Could not remove stale temp download {tmp_path}: {e}")

    req = urllib.request.Request(download_url, headers={"User-Agent": "grammar-ai-updater"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp_path, "wb") as f:
            shutil.copyfileobj(resp, f)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
    os.replace(tmp_path, dest_path)

    # Mark of the Web - the same zone-identifier a browser writes for anything it
    # downloads from the internet. Deliberately not skipped: a manual browser download
    # of this same file would carry it too, so this keeps SmartScreen's behavior
    # consistent with a manual download rather than looking like an attempt to dodge it.
    try:
        # newline="" disables text-mode's universal-newline translation - without it,
        # the \n in this literal gets *also* expanded to \r\n on write, doubling up
        # to \r\r\n alongside the already-literal \r.
        with open(f"{dest_path}:Zone.Identifier", "w", encoding="utf-8", newline="") as zf:
            zf.write("[ZoneTransfer]\r\nZoneId=3\r\n")
    except OSError as e:
        logger.debug(f"Could not set Mark-of-the-Web on downloaded installer: {e}")

    return dest_path


def open_containing_folder(path: Path) -> None:
    """Open Explorer with `path` selected. Never executes the file itself."""
    subprocess.Popen(f'explorer /select,"{path}"')

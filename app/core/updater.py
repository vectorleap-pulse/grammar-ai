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
import hashlib
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
    size: int
    digest: str


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
        size = 0
        digest = ""
        for asset in data.get("assets") or []:
            name = asset.get("name", "")
            if name.endswith(".exe"):
                download_url = asset.get("browser_download_url", "")
                # .get(key, default) only applies default when the key is absent, not
                # when the API returns an explicit null - guard both with `or` too.
                size = asset.get("size", 0) or 0
                digest = asset.get("digest", "") or ""
                break

        if not download_url:
            logger.warning("Update check found a new release but no installer asset on it")
            return None

        return UpdateInfo(
            version=latest,
            release_url=html_url,
            download_url=download_url,
            size=size,
            digest=digest,
        )
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


def _sha256_of(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Stream `path` through SHA256 in chunks, avoiding loading it fully into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_download(path: Path, expected_size: int, expected_digest: str) -> None:
    """Raise ValueError if `path` doesn't match the release asset's reported size/digest.

    This catches accidental corruption or truncation (a crash mid-write, a flaky
    network, a stale/partial file left over from a previous run) - it is not an
    anti-tampering or supply-chain control, since expected_size/expected_digest were
    fetched over the same HTTPS channel as the file itself.

    A 0-byte file is always rejected, regardless of what expected_size/expected_digest
    say - there's no legitimate 0-byte installer, and this is the one case where
    trusting "no signal to check against" would let a fully-empty/failed download
    through undetected. expected_size is otherwise only enforced when non-zero (GitHub
    always reports it, but this degrades gracefully rather than false-failing if it's
    ever genuinely missing). expected_digest ("sha256:<hex>", a newer API field that
    may be blank for assets uploaded before GitHub started computing it) only gates
    the checksum check when present - a missing digest skips that check, but a
    present-and-mismatched one always fails.
    """
    actual_size = path.stat().st_size
    if actual_size == 0:
        raise ValueError("downloaded file is empty")
    if expected_size and actual_size != expected_size:
        raise ValueError(f"size mismatch: expected {expected_size} bytes, got {actual_size}")

    if expected_digest:
        algo, _, expected_hex = expected_digest.strip().lower().partition(":")
        if algo == "sha256" and expected_hex:
            actual_hex = _sha256_of(path).lower()
            if actual_hex != expected_hex:
                raise ValueError("sha256 checksum mismatch")


def _clear_stale_temp_download(tmp_path: Path) -> None:
    if tmp_path.exists():
        try:
            tmp_path.unlink()
        except OSError as e:
            logger.debug(f"Could not remove stale temp download {tmp_path}: {e}")


def download_installer(
    download_url: str, dest_dir: Path, expected_size: int = 0, expected_digest: str = ""
) -> Path:
    """Download the installer asset into dest_dir, returning its final path.

    Idempotent: if a file with the expected (already version-qualified) name already
    exists and passes verification, the download is skipped entirely and that file is
    returned as-is - this covers both a repeated check within one session and a later
    session finding a file downloaded, but not yet installed, previously. An existing
    file that fails verification is deleted and re-downloaded rather than trusted.

    Downloads to a temp path first and only os.replace()s it onto the final name once
    the stream completes without error, so a crash/kill mid-download never leaves a
    truncated file sitting at the path the idempotency check above looks for. The
    freshly downloaded file is verified the same way before being handed back - on
    failure it's deleted and never marked with the Mark-of-the-Web or returned.
    """
    filename = download_url.rsplit("/", 1)[-1].split("?", 1)[0].split("#", 1)[0]
    dest_path = dest_dir / filename
    tmp_path = dest_dir / f"{filename}.part"
    _clear_stale_temp_download(tmp_path)

    if dest_path.exists():
        try:
            _verify_download(dest_path, expected_size, expected_digest)
            return dest_path
        except ValueError as e:
            logger.warning(f"Existing download failed verification, re-downloading: {e}")
            dest_path.unlink()

    dest_dir.mkdir(parents=True, exist_ok=True)

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

    try:
        _verify_download(dest_path, expected_size, expected_digest)
    except ValueError:
        dest_path.unlink()
        raise

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

"""Shared clipboard/keyboard-state helpers for hotkey capture and paste-back."""

import ctypes
import sys
import time

try:
    import pyperclip
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyperclip = None  # type: ignore[assignment]

_IS_WIN = sys.platform == "win32"

VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt

# Delay after a simulated Ctrl+A before Ctrl+C - lets the target app finish
# updating its selection before the copy, avoiding a race where a Ctrl+C fired
# immediately after Ctrl+A returns stale/incomplete clipboard content on apps
# that process the select-all asynchronously.
SELECT_ALL_SETTLE_SECONDS = 0.05


def poll_clipboard(timeout: float) -> str:
    """Return clipboard text as soon as it becomes non-empty, or after timeout."""
    assert pyperclip is not None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(0.025)
        text = pyperclip.paste()
        if text:
            return text
    return ""


def wait_for_keys_released(vks: list[int], timeout: float = 1.0) -> bool:
    """Block until none of `vks` are physically held down, or `timeout` elapses.

    Hotkeys built from real key combos (a global Ctrl+Alt+<letter>, or an in-app
    Alt+<digit> shortcut) fire on key-*down*, while the user is very likely still
    physically holding the modifier(s). Simulating Ctrl+C/Ctrl+A/Ctrl+V immediately
    afterward risks those still-held modifiers combining with our synthetic
    keystrokes into an unintended combo - Windows treats Ctrl+Alt as AltGr-equivalent
    for character generation, which many apps/layouts resolve to typing a literal
    character instead of running the clipboard shortcut, corrupting the target
    field. Waiting for a clean release (checked via `GetAsyncKeyState`, independent
    of any window's focus or message queue) avoids that race.

    Returns True once a clean release is confirmed, False if `timeout` elapsed
    while a key was still held - callers must treat False as "do not proceed",
    since going ahead anyway is exactly the corruption this function exists to
    prevent.
    """
    if not _IS_WIN:
        return True
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in vks):
            return True
        time.sleep(0.01)
    return False

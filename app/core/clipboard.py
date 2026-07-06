"""Shared clipboard polling helper for hotkey capture and paste-back."""

import time

try:
    import pyperclip
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyperclip = None  # type: ignore[assignment]


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

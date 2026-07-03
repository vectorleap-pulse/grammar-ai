"""Write polished/translated text back into the originating control via UI Automation.

No clipboard access, no simulated keystrokes, no SetForegroundWindow-driven "select
all and replace" trick - the text is written directly into the control that was
captured at hotkey time via ValuePattern.SetValue. If that control reference has
gone stale (the source app closed, or enough time passed that the automation
element is no longer valid), focus is restored to the original window and the
currently-focused control is re-resolved as a one-shot recovery attempt - this
still never touches the clipboard.
"""

import ctypes
import sys
import time
from typing import Optional

from loguru import logger

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    import uiautomation as auto


def get_foreground_window() -> int:
    if _IS_WIN:
        return ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
    return 0


def _is_control_alive(control: "Optional[auto.Control]") -> bool:
    if control is None:
        return False
    try:
        # Touching a property forces a live COM round-trip; a stale/dead element raises.
        control.GetRuntimeId()
        return True
    except Exception:
        return False


def _write_value(control: "auto.Control", original: str, new_text: str) -> bool:
    value_pattern = control.GetPattern(auto.PatternId.ValuePattern)
    if not value_pattern:
        return False
    if value_pattern.IsReadOnly:
        return False

    current = value_pattern.Value or ""
    if original and original in current:
        replacement = current.replace(original, new_text, 1)
    else:
        replacement = new_text
    return bool(value_pattern.SetValue(replacement))


def restore_focus_and_paste(
    control: "Optional[auto.Control]", hwnd: int, original: str, polished: str
) -> bool:
    """Write `polished` into `control` (replacing `original` if still present).

    Returns True on success. Never touches the clipboard.
    """
    if not _IS_WIN:
        return False

    target = control if _is_control_alive(control) else None

    if target is None and hwnd:
        try:
            ctypes.windll.user32.SetForegroundWindow(hwnd)  # type: ignore[attr-defined]
            time.sleep(0.05)
            target = auto.GetFocusedControl()
        except Exception as e:
            logger.debug(f"Could not restore foreground window for paste-back: {e}")
            target = None

    if target is None:
        logger.warning("No live control available for paste-back")
        return False

    try:
        ok = _write_value(target, original, polished)
        if ok:
            logger.debug("Pasted via UI Automation ValuePattern.SetValue")
        else:
            logger.debug("Target control does not support writable ValuePattern")
        return ok
    except Exception as e:
        logger.warning(f"UI Automation paste-back failed: {e}")
        return False

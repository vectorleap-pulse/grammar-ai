"""Windows foreground-window tracking and focus restoration for the Use button."""

import ctypes
import sys
import time

import pyautogui
import pyperclip
from loguru import logger

_IS_WIN = sys.platform == "win32"


def get_foreground_window() -> int:
    if _IS_WIN:
        return ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
    return 0


def restore_focus_and_paste(hwnd: int, original: str, polished: str) -> bool:
    """Focus hwnd, read full window text via Ctrl+A+C, replace original with polished, paste back."""
    if not _IS_WIN or not hwnd:
        return False
    try:
        ctypes.windll.user32.SetForegroundWindow(hwnd)  # type: ignore[attr-defined]
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.1)

        window_text = pyperclip.paste()
        if original in window_text:
            result = window_text.replace(original, polished, 1)
        else:
            # original not found (window changed) — fall back to replacing all selected text
            result = polished

        pyperclip.copy(result)
        pyautogui.hotkey("ctrl", "v")
        logger.debug(f"Pasted to hwnd={hwnd}")
        return True
    except Exception as e:
        logger.warning(f"restore_focus_and_paste failed: {e}")
        return False

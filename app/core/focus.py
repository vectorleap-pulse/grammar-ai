"""Windows foreground-window tracking and focus restoration for the Use button."""

import ctypes
import sys
import time

from loguru import logger

_IS_WIN = sys.platform == "win32"


def get_foreground_window() -> int:
    if _IS_WIN:
        return ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
    return 0


def restore_focus_and_paste(hwnd: int, text: str) -> bool:
    """Focus hwnd, then simulate Ctrl+A + Ctrl+V to replace text in-place."""
    if not _IS_WIN or not hwnd:
        return False
    try:
        import pyautogui
        import pyperclip

        pyperclip.copy(text)
        ctypes.windll.user32.SetForegroundWindow(hwnd)  # type: ignore[attr-defined]
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        logger.debug(f"Pasted to hwnd={hwnd}")
        return True
    except Exception as e:
        logger.warning(f"restore_focus_and_paste failed: {e}")
        return False

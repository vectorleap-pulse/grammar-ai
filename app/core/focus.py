"""Write polished text back into the originating window via clipboard + simulated paste.

Blanks the clipboard, selects all and copies to read the control's *current* full
content (which may have changed since capture), replaces the captured `original`
substring within that live text with the polished result, writes the merged text
back to the clipboard, then selects all and pastes - restoring the user's prior
clipboard contents afterward. This mirrors hotkey.py's capture mechanism (same
clipboard-blank/simulate-keys/poll/restore family, applied to writing instead of
reading), trading the same AV-heuristic risk for compatibility with apps where a
real simulated paste succeeds but direct UI Automation writes don't.
"""

import ctypes
import sys
import time

from loguru import logger

from app.core.clipboard import poll_clipboard

_IS_WIN = sys.platform == "win32"

try:
    import pyautogui
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyautogui = None  # type: ignore[assignment]

try:
    import pyperclip
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyperclip = None  # type: ignore[assignment]


def bring_to_foreground(hwnd: int) -> None:
    """Force `hwnd` (one of Grammar AI's own windows) to the OS foreground.

    Plain SetForegroundWindow/pywebview's window.show()+restore() aren't enough when
    called off the back of a global RegisterHotKey combo: WM_HOTKEY lands on a
    background thread of this process (see hotkey.py), not on the window belonging
    to whatever app the user was actually typing into, and Windows doesn't treat
    "this process just handled a global hotkey" as automatic license to steal
    foreground focus from it. Windows denies a foreground-switch
    request from any process that isn't the current foreground process, wasn't
    launched by it, or didn't generate the last input event, and flashes the taskbar
    button instead. AttachThreadInput temporarily shares the calling thread's input
    state with the foreground thread, which is the standard, documented way to
    legitimately grant a background process that eligibility for one call.
    """
    if not _IS_WIN or not hwnd:
        return
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    fg_hwnd = user32.GetForegroundWindow()
    if fg_hwnd == hwnd:
        return
    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
    cur_thread = ctypes.windll.kernel32.GetCurrentThreadId()  # type: ignore[attr-defined]
    attached = False
    try:
        if fg_thread and fg_thread != cur_thread:
            attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
        user32.SetForegroundWindow(hwnd)
    except Exception as e:
        logger.debug(f"bring_to_foreground failed: {e}")
    finally:
        if attached:
            user32.AttachThreadInput(cur_thread, fg_thread, False)


def restore_focus_and_paste(hwnd: int, original: str, polished: str) -> bool:
    """Replace `original` with `polished` in whatever window `hwnd` refers to.

    Returns True on success. Restores the user's clipboard contents afterward.
    """
    if not _IS_WIN or not hwnd or pyautogui is None or pyperclip is None:
        return False

    bring_to_foreground(hwnd)
    time.sleep(0.05)
    if ctypes.windll.user32.GetForegroundWindow() != hwnd:  # type: ignore[attr-defined]
        logger.warning("Could not bring original window to foreground for paste-back")
        return False

    original_clipboard = pyperclip.paste()
    try:
        pyperclip.copy("")
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "c")
        current = poll_clipboard(timeout=0.4)

        if original and original in current:
            replacement = current.replace(original, polished, 1)
        else:
            replacement = polished

        pyperclip.copy(replacement)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
        logger.debug("Pasted via clipboard/simulated Ctrl+V")
        return True
    finally:
        pyperclip.copy(original_clipboard or "")

"""Global hotkey via Win32 RegisterHotKey, delivered as WM_HOTKEY on a dedicated thread.

Polish fires on Ctrl+Alt+S, Translate on Ctrl+Alt+D - real key combos, so
`RegisterHotKey` can register them directly (no need for the low-level keyboard
hook a "double-tap a lone modifier" scheme would require). Each `HotkeyManager`
runs its own thread whose only job is to pump `GetMessageW` for its registered
hotkey ID: `RegisterHotKey(hWnd=None, ...)` ties the registration to the calling
thread's message queue rather than to a window, so that thread must stay alive
with a live message loop for as long as the hotkey should fire.

Capture (reading the focused control's text) is clipboard-based: blank the
clipboard, simulate Ctrl+C, poll for the result, restore the original contents -
falling back to Ctrl+A, Ctrl+C if nothing was selected. `last_hwnd` (the
foreground window at hotkey time) is the only thing remembered for paste-back
(`focus.py`) - it also uses the clipboard, not a captured control reference.
"""

import ctypes
import ctypes.wintypes
import itertools
import sys
import threading
import time
from typing import Callable, Optional

from loguru import logger

from app.core.clipboard import (
    SELECT_ALL_SETTLE_SECONDS,
    VK_CONTROL,
    VK_MENU,
    poll_clipboard,
    wait_for_keys_released,
)

_IS_WIN = sys.platform == "win32"

try:
    import pyautogui
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyautogui = None  # type: ignore[assignment]

try:
    import pyperclip
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyperclip = None  # type: ignore[assignment]

WM_QUIT = 0x0012
WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000

_hotkey_ids = itertools.count(1)

if _IS_WIN:
    _user32 = ctypes.windll.user32  # type: ignore[attr-defined]

    _user32.RegisterHotKey.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.c_int,
        ctypes.wintypes.UINT,
        ctypes.wintypes.UINT,
    ]
    _user32.RegisterHotKey.restype = ctypes.wintypes.BOOL
    _user32.UnregisterHotKey.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
    _user32.UnregisterHotKey.restype = ctypes.wintypes.BOOL


class HotkeyManager:
    def __init__(
        self,
        on_text: Callable[[str], None],
        modifiers: int,
        vk: int,
        description: str,
    ) -> None:
        self.on_text = on_text
        self.last_hwnd: int = 0
        self._enabled = False
        self._tid: int = 0
        self._thread: Optional[threading.Thread] = None
        self._capture_lock = threading.Lock()
        self._description = description
        self._modifiers = modifiers | MOD_NOREPEAT
        self._vk = vk
        self._hotkey_id = next(_hotkey_ids)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        if not _IS_WIN or self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()
        logger.info(f"Hotkey {self._description} enabled (RegisterHotKey)")

    def disable(self) -> None:
        if not self._enabled:
            return
        self._enabled = False
        if self._tid:
            ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)  # type: ignore[attr-defined]
        logger.info("Hotkey disabled")

    def _message_loop(self) -> None:
        self._tid = ctypes.windll.kernel32.GetCurrentThreadId()  # type: ignore[attr-defined]
        if not _user32.RegisterHotKey(None, self._hotkey_id, self._modifiers, self._vk):
            err = ctypes.GetLastError()  # type: ignore[attr-defined]
            logger.error(
                f"RegisterHotKey failed for {self._description} (error {err}) - hotkey unavailable"
            )
            self._enabled = False
            return

        msg = ctypes.wintypes.MSG()
        try:
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:  # type: ignore[attr-defined]
                if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
                    self.last_hwnd = ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
                    threading.Thread(target=self._capture, daemon=True).start()
        finally:
            _user32.UnregisterHotKey(None, self._hotkey_id)

    def _capture(self) -> None:
        if not self._capture_lock.acquire(blocking=False):
            logger.debug("Hotkey fired during active capture - ignored")
            return
        try:
            self._do_capture()
        finally:
            self._capture_lock.release()

    def _do_capture(self) -> None:
        if pyautogui is None or pyperclip is None:
            logger.warning("pyautogui/pyperclip not available - hotkey capture unavailable")
            return

        # WM_HOTKEY fires on key-down of the combo's last key, while the user is
        # very likely still physically holding it - simulating Ctrl+C before that
        # clears risks it combining with the still-held modifiers (see
        # wait_for_keys_released's docstring). If the combo is still held once the
        # wait times out, abort rather than risk corrupting the source field.
        if not wait_for_keys_released([VK_CONTROL, VK_MENU, self._vk]):
            logger.warning(
                f"Hotkey {self._description} still held after timeout - aborting capture"
            )
            return

        original_clipboard = pyperclip.paste()
        try:
            pyperclip.copy("")
            pyautogui.hotkey("ctrl", "c")
            text = poll_clipboard(timeout=0.4)

            if not text or not text.strip():
                # Nothing was selected - select all then copy.
                pyautogui.hotkey("ctrl", "a")
                time.sleep(SELECT_ALL_SETTLE_SECONDS)
                pyperclip.copy("")
                pyautogui.hotkey("ctrl", "c")
                text = poll_clipboard(timeout=0.4)

            if text and text.strip():
                logger.info(f"Hotkey captured {len(text)} chars via clipboard")
                self.on_text(text.strip())
            else:
                logger.debug("Clipboard was empty after hotkey capture")
        finally:
            pyperclip.copy(original_clipboard or "")

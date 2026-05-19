"""Global hotkey via Win32 RegisterHotKey — reliable across apps and system load."""

import ctypes
import ctypes.wintypes
import sys
import threading
import time
from typing import Callable

import pyautogui
import pyperclip
from loguru import logger

_IS_WIN = sys.platform == "win32"

WM_HOTKEY   = 0x0312
WM_QUIT     = 0x0012
MOD_CONTROL = 0x0002
MOD_SHIFT   = 0x0004
VK_SPACE    = 0x20

_HOTKEY_ID = 1


class HotkeyManager:
    def __init__(self, on_text: Callable[[str], None]) -> None:
        self.on_text = on_text
        self.last_hwnd: int = 0
        self._enabled = False
        self._tid: int = 0
        self._thread: threading.Thread | None = None
        self._capture_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        if not _IS_WIN or self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()
        logger.info("Hotkey Ctrl+Shift+Space enabled (RegisterHotKey)")

    def disable(self) -> None:
        if not self._enabled:
            return
        self._enabled = False
        if self._tid:
            ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        logger.info("Hotkey disabled")

    def _message_loop(self) -> None:
        self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
        ok = ctypes.windll.user32.RegisterHotKey(
            None, _HOTKEY_ID, MOD_CONTROL | MOD_SHIFT, VK_SPACE
        )
        if not ok:
            err = ctypes.GetLastError()
            logger.error(f"RegisterHotKey failed (error {err}) — hotkey unavailable")
            self._enabled = False
            return

        msg = ctypes.wintypes.MSG()
        try:
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                    # Capture the source window before anything can shift focus.
                    self.last_hwnd = ctypes.windll.user32.GetForegroundWindow()
                    threading.Thread(target=self._capture, daemon=True).start()
        finally:
            ctypes.windll.user32.UnregisterHotKey(None, _HOTKEY_ID)

    def _capture(self) -> None:
        if not self._capture_lock.acquire(blocking=False):
            logger.debug("Hotkey fired during active capture — ignored")
            return
        try:
            self._do_capture()
        finally:
            self._capture_lock.release()

    def _do_capture(self) -> None:
        # Release modifiers so ctrl+c isn't mis-read as ctrl+shift+c.
        pyautogui.keyUp("shift")
        pyautogui.keyUp("ctrl")
        time.sleep(0.05)

        pyperclip.copy("")
        pyautogui.hotkey("ctrl", "c")
        text = self._poll_clipboard(timeout=0.4)

        if not text or not text.strip():
            # Nothing selected — select all then copy.
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyperclip.copy("")
            pyautogui.hotkey("ctrl", "c")
            text = self._poll_clipboard(timeout=0.4)

        if text and text.strip():
            logger.info(f"Hotkey captured {len(text)} chars")
            self.on_text(text.strip())
        else:
            logger.debug("Clipboard was empty after hotkey capture")

    @staticmethod
    def _poll_clipboard(timeout: float) -> str:
        """Return clipboard text as soon as it becomes non-empty, or after timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(0.025)
            text = pyperclip.paste()
            if text:
                return text
        return ""

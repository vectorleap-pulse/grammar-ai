"""Global hotkey via Win32 RegisterHotKey, capture via UI Automation.

Text is read directly from the focused control's ValuePattern/TextPattern - no
clipboard access and no synthetic keystrokes are involved. This matters beyond
correctness: a hotkey handler that blanks the clipboard, simulates Ctrl+C, polls
for the result, and restores the original contents is structurally identical to
how clipboard-hijacking malware behaves, and gets flagged as such by some AV/EDR
heuristics (Bitdefender among them). UI Automation reads the control's text as a
direct, synchronous COM call instead.
"""

import ctypes
import ctypes.wintypes
import sys
import threading
import time
from typing import Callable, Optional

from loguru import logger

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    import uiautomation as auto

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_SPACE = 0x20

_HOTKEY_ID_POLISH = 1
_HOTKEY_ID_TRANSLATE = 2

# Keep for backward compat
_HOTKEY_ID = _HOTKEY_ID_POLISH

# Chromium/Electron (and some other frameworks) only build their full accessibility
# tree once a UI Automation client is detected querying them, so the very first read
# right after the hotkey fires can come back empty even though the control does
# support the pattern. One short retry covers that "cold start" without adding a
# perceptible delay for controls that were already accessibility-active.
_COLD_START_RETRY_DELAY_SECONDS = 0.15


def _read_control_text(control: "Optional[auto.Control]") -> str:
    """Read the focused control's (selected, or full) text via UI Automation. No clipboard."""
    if control is None:
        return ""

    try:
        text_pattern = control.GetPattern(auto.PatternId.TextPattern)
    except Exception:
        text_pattern = None
    if text_pattern:
        try:
            selection = text_pattern.GetSelection()
            if selection:
                selected = selection[0].GetText(-1)
                if selected and selected.strip():
                    return selected
            return text_pattern.DocumentRange.GetText(-1)
        except Exception as e:
            logger.debug(f"TextPattern read failed: {e}")

    try:
        value_pattern = control.GetPattern(auto.PatternId.ValuePattern)
    except Exception:
        value_pattern = None
    if value_pattern:
        try:
            return value_pattern.Value or ""
        except Exception as e:
            logger.debug(f"ValuePattern read failed: {e}")

    return ""


class HotkeyManager:
    def __init__(
        self,
        on_text: Callable[[str], None],
        modifiers: int = MOD_CONTROL | MOD_SHIFT,
        vk: int = VK_SPACE,
        hotkey_id: int = _HOTKEY_ID_POLISH,
        description: str = "Ctrl+Shift+Space",
    ) -> None:
        self.on_text = on_text
        self.last_hwnd: int = 0
        self.last_control: Optional["auto.Control"] = None
        self._enabled = False
        self._tid: int = 0
        self._thread: Optional[threading.Thread] = None
        self._capture_lock = threading.Lock()
        self._modifiers = modifiers
        self._vk = vk
        self._hotkey_id = hotkey_id
        self._description = description

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
        ok = ctypes.windll.user32.RegisterHotKey(  # type: ignore[attr-defined]
            None, self._hotkey_id, self._modifiers, self._vk
        )
        if not ok:
            err = ctypes.GetLastError()  # type: ignore[attr-defined]
            logger.error(f"RegisterHotKey failed (error {err}) - hotkey unavailable")
            self._enabled = False
            return

        msg = ctypes.wintypes.MSG()
        try:
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:  # type: ignore[attr-defined]
                if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
                    # Capture the source window before anything can shift focus.
                    self.last_hwnd = ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
                    threading.Thread(target=self._capture, daemon=True).start()
        finally:
            ctypes.windll.user32.UnregisterHotKey(None, self._hotkey_id)  # type: ignore[attr-defined]

    def _capture(self) -> None:
        if not self._capture_lock.acquire(blocking=False):
            logger.debug("Hotkey fired during active capture - ignored")
            return
        try:
            self._do_capture()
        finally:
            self._capture_lock.release()

    def _do_capture(self) -> None:
        try:
            control = auto.GetFocusedControl()
            text = _read_control_text(control)
            if not text.strip():
                # Cold-start retry: give a Chromium/Electron accessibility tree a
                # moment to activate before concluding there's nothing to read.
                time.sleep(_COLD_START_RETRY_DELAY_SECONDS)
                control = auto.GetFocusedControl()
                text = _read_control_text(control)
        except Exception as e:
            logger.warning(f"UI Automation capture failed: {e}")
            return

        if text and text.strip():
            logger.info(f"Hotkey captured {len(text)} chars via UI Automation")
            self.last_control = control
            self.on_text(text.strip())
        else:
            logger.debug(
                "Focused control exposed no readable text (unsupported app or empty field)"
            )

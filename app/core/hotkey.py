"""Global hotkey: Ctrl+Shift+Space — select-all, copy, then trigger LLM."""

import threading
import time
from typing import Callable

from loguru import logger

try:
    import keyboard as _kb

    _HAS_KB = True
except ImportError:
    _HAS_KB = False
    logger.warning("'keyboard' module unavailable; global hotkey disabled")

HOTKEYS = ["ctrl", "shift", "space"]
HOTKEY = "+".join(HOTKEYS)


class HotkeyManager:
    def __init__(self, on_text: Callable[[str], None]) -> None:
        self.on_text = on_text
        self.last_hwnd: int = 0
        self._enabled = False
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        if not _HAS_KB:
            return
        with self._lock:
            if not self._enabled:
                _kb.add_hotkey(HOTKEY, self._dispatch, suppress=False)
                self._enabled = True
                logger.info(f"Hotkey {HOTKEY} enabled")

    def disable(self) -> None:
        if not _HAS_KB:
            return
        with self._lock:
            if self._enabled:
                try:
                    _kb.remove_hotkey(HOTKEY)
                except (KeyError, ValueError) as e:
                    logger.debug(f"Hotkey {HOTKEY} was not registered: {e}")
                self._enabled = False
                logger.info(f"Hotkey {HOTKEY} disabled")

    def _dispatch(self) -> None:
        # Run capture in a separate thread so we don't block the hook thread.
        threading.Thread(target=self._capture, daemon=True).start()

    def _capture(self) -> None:
        import pyautogui
        import pyperclip

        from app.core.focus import get_foreground_window

        # Record which window had focus before we steal it.
        self.last_hwnd = get_foreground_window()

        # Explicitly release all modifier keys to prevent key bleed.
        for key in HOTKEYS:
            pyautogui.keyUp(key)
        time.sleep(0.05)

        # Clear the clipboard to detect if copy actually works.
        pyperclip.copy("")

        # Try copying the current selection first.
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.05)
        text = pyperclip.paste()

        if not text or not text.strip():
            # Nothing was selected — fall back to select-all then copy.
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.05)
            text = pyperclip.paste()

        if text and text.strip():
            logger.info(f"Hotkey captured {len(text)} chars")
            self.on_text(text.strip())
        else:
            logger.debug("Hotkey fired but clipboard was empty")

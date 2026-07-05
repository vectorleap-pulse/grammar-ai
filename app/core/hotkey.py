"""Global hotkey via a low-level keyboard hook, triggered by double-tapping a modifier.

Polish fires on double-tap Alt, Translate on double-tap Ctrl - no letter key
involved. `RegisterHotKey` can't represent "a lone modifier pressed twice", so this
watches every keystroke via a WH_KEYBOARD_LL hook and times modifier taps itself,
tracking every currently-held key (not just the tracked modifier) so a tap that
happens as part of any chord (Ctrl+Shift, Alt+Shift, Shift+Arrow, Shift+letter while
typing, etc.) is never mistaken for a solo double-tap.

Polish's capture (reading the focused control's text) is done directly via UI
Automation ValuePattern/TextPattern - no clipboard access and no synthetic
keystrokes. This matters beyond correctness: a hotkey handler that blanks the
clipboard, simulates Ctrl+C, polls for the result, and restores the original
contents is structurally identical to how clipboard-hijacking malware behaves, and
gets flagged as such by some AV/EDR heuristics (Bitdefender among them).

Translate's capture is a deliberate, scoped exception (`capture_via_clipboard=True`):
it uses that clipboard-based approach, trading the same AV-heuristic risk for
broader compatibility with apps that don't expose text via accessibility APIs. This
only affects how Translate's input is read - there is no paste-back for Translate.
"""

import ctypes
import ctypes.wintypes
import sys
import threading
import time
from typing import Any, Callable, Literal, Optional

from loguru import logger

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    import uiautomation as auto

try:
    import pyautogui
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyautogui = None  # type: ignore[assignment]

try:
    import pyperclip
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyperclip = None  # type: ignore[assignment]

WM_QUIT = 0x0012
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5

_DOUBLE_TAP_WINDOW_SECONDS = 0.4

# Chromium/Electron (and some other frameworks) only build their full accessibility
# tree once a UI Automation client is detected querying them, so the very first read
# right after the hotkey fires can come back empty even though the control does
# support the pattern. One short retry covers that "cold start" without adding a
# perceptible delay for controls that were already accessibility-active.
_COLD_START_RETRY_DELAY_SECONDS = 0.15


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


_LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, ctypes.wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT)
)

if _IS_WIN:
    _user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    _kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    _user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int,
        _LowLevelKeyboardProc,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
    ]
    _user32.SetWindowsHookExW.restype = ctypes.c_void_p
    _user32.CallNextHookEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.wintypes.WPARAM,
        ctypes.POINTER(KBDLLHOOKSTRUCT),
    ]
    _user32.CallNextHookEx.restype = ctypes.c_ssize_t
    _user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
    _user32.UnhookWindowsHookEx.restype = ctypes.wintypes.BOOL
    _kernel32.GetModuleHandleW.argtypes = [ctypes.wintypes.LPCWSTR]
    _kernel32.GetModuleHandleW.restype = ctypes.c_void_p


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
        tap_key: Literal["shift", "control", "alt"] = "shift",
        description: str = "Double Shift",
        capture_via_clipboard: bool = False,
    ) -> None:
        self.on_text = on_text
        self.last_hwnd: int = 0
        self.last_control: Optional["auto.Control"] = None
        self._enabled = False
        self._tid: int = 0
        self._thread: Optional[threading.Thread] = None
        self._capture_lock = threading.Lock()
        self._description = description
        self._capture_via_clipboard = capture_via_clipboard
        self._own_vks = {
            "shift": {VK_LSHIFT, VK_RSHIFT},
            "control": {VK_LCONTROL, VK_RCONTROL},
            "alt": {VK_LMENU, VK_RMENU},
        }[tap_key]
        self._keys_down: set[int] = set()
        self._pending_tap_time: Optional[float] = None
        self._hook_handle: Optional[int] = None
        self._hook_proc: Optional[Any] = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        if not _IS_WIN or self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()
        logger.info(f"Hotkey {self._description} enabled (low-level keyboard hook)")

    def disable(self) -> None:
        if not self._enabled:
            return
        self._enabled = False
        if self._tid:
            ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)  # type: ignore[attr-defined]
        logger.info("Hotkey disabled")

    def _message_loop(self) -> None:
        self._tid = ctypes.windll.kernel32.GetCurrentThreadId()  # type: ignore[attr-defined]
        self._hook_proc = _LowLevelKeyboardProc(self._hook_callback)
        self._hook_handle = _user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._hook_proc, _kernel32.GetModuleHandleW(None), 0
        )
        if not self._hook_handle:
            err = ctypes.GetLastError()  # type: ignore[attr-defined]
            logger.error(f"SetWindowsHookExW failed (error {err}) - hotkey unavailable")
            self._enabled = False
            return

        msg = ctypes.wintypes.MSG()
        try:
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:  # type: ignore[attr-defined]
                pass
        finally:
            _user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None
            self._hook_proc = None

    def _hook_callback(
        self, n_code: int, w_param: int, l_param: "ctypes._Pointer[KBDLLHOOKSTRUCT]"
    ) -> int:
        if n_code < 0:
            return _user32.CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

        vk = l_param.contents.vkCode
        is_down = w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)
        is_up = w_param in (WM_KEYUP, WM_SYSKEYUP)

        if is_down and vk not in self._keys_down:
            had_other_keys_down = bool(self._keys_down)
            self._keys_down.add(vk)
            if vk in self._own_vks:
                if had_other_keys_down:
                    # This tap happened as part of a chord with something else
                    # (Ctrl+Shift, Alt+Shift, Win+Shift, Shift+Arrow, Shift+letter
                    # while typing, etc.) - not a solo tap, don't count it.
                    self._pending_tap_time = None
                else:
                    now = time.monotonic()
                    if (
                        self._pending_tap_time is not None
                        and now - self._pending_tap_time <= _DOUBLE_TAP_WINDOW_SECONDS
                    ):
                        self.last_hwnd = ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
                        threading.Thread(target=self._capture, daemon=True).start()
                        self._pending_tap_time = None
                    else:
                        self._pending_tap_time = now
            elif self._keys_down & self._own_vks:
                # A real key was pressed while our modifier was held - that was a
                # combo, not a solo tap.
                self._pending_tap_time = None
        elif is_up:
            self._keys_down.discard(vk)

        return _user32.CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

    def _capture(self) -> None:
        if not self._capture_lock.acquire(blocking=False):
            logger.debug("Hotkey fired during active capture - ignored")
            return
        try:
            if self._capture_via_clipboard:
                self._do_capture_via_clipboard()
            else:
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

    def _do_capture_via_clipboard(self) -> None:
        if pyautogui is None or pyperclip is None:
            logger.warning("pyautogui/pyperclip not available - clipboard capture unavailable")
            return

        original_clipboard = pyperclip.paste()
        try:
            pyperclip.copy("")
            pyautogui.hotkey("ctrl", "c")
            text = self._poll_clipboard(timeout=0.4)

            if not text or not text.strip():
                # Nothing was selected - select all then copy.
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.05)
                pyperclip.copy("")
                pyautogui.hotkey("ctrl", "c")
                text = self._poll_clipboard(timeout=0.4)

            if text and text.strip():
                logger.info(f"Hotkey captured {len(text)} chars via clipboard")
                self.on_text(text.strip())
            else:
                logger.debug("Clipboard was empty after hotkey capture")
        finally:
            pyperclip.copy(original_clipboard or "")

    @staticmethod
    def _poll_clipboard(timeout: float) -> str:
        """Return clipboard text as soon as it becomes non-empty, or after timeout."""
        assert pyperclip is not None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(0.025)
            text = pyperclip.paste()
            if text:
                return text
        return ""

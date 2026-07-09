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
import re
import sys
import threading
import time

from loguru import logger

from app.core.clipboard import (
    SELECT_ALL_SETTLE_SECONDS,
    VK_MENU,
    poll_clipboard,
    wait_for_keys_released,
)

# Best-effort buffer given to the target app to finish reading the clipboard after
# a simulated Ctrl+V before the original clipboard contents are restored over it -
# restoring too early risks the app instead pasting the stale original content it
# hasn't read past yet (see restore_focus_and_paste). Applied on a background
# timer so it doesn't add latency to the (synchronous) caller.
_CLIPBOARD_RESTORE_DELAY_SECONDS = 0.4

# Serializes paste-back calls end-to-end, including the deferred restore above -
# two calls racing over the same physical clipboard is exactly how one call's
# restore could clobber another's in-flight read/write. A bounded timeout means a
# stuck holder degrades to "abort this call" rather than an indefinite UI hang.
_paste_lock = threading.Lock()
_PASTE_LOCK_TIMEOUT_SECONDS = 3.0

_IS_WIN = sys.platform == "win32"

try:
    import pyautogui
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyautogui = None  # type: ignore[assignment]

try:
    import pyperclip
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyperclip = None  # type: ignore[assignment]


def _normalize_newlines(text: str) -> str:
    """Collapse \\r\\n and \\r to \\n so a partial-selection copy and a Ctrl+A
    whole-buffer copy of the same text compare equal regardless of which
    line-ending convention the target app used for each.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _find_normalized(haystack: str, needle: str) -> tuple[int, int] | None:
    """Find `needle` inside `haystack`, treating any of \\r\\n, \\r, or \\n in
    `needle` as equivalent to any of those in `haystack` (a partial-selection
    copy and a Ctrl+A whole-buffer copy of the same text can report different
    line-ending conventions for the same underlying content - see
    _normalize_newlines). Returns the matched span in `haystack`'s own
    unmodified coordinates, so the caller can splice around it without
    altering any of `haystack`'s original text (including its line endings)
    outside the match.
    """
    if not needle:
        return None
    pattern = "".join(
        r"(?:\r\n|\r|\n)" if ch == "\n" else re.escape(ch) for ch in _normalize_newlines(needle)
    )
    match = re.search(pattern, haystack)
    return match.span() if match else None


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


def _finish_restore(value: str, *, delayed: bool) -> None:
    """Restore `value` to the clipboard and release `_paste_lock` - exactly once.

    Runs on a delayed background timer when `delayed` is True (a paste was
    actually sent and the target app needs time to read it before the clipboard
    changes again - see _CLIPBOARD_RESTORE_DELAY_SECONDS), or immediately
    otherwise (nothing was pasted, so there's nothing to wait for).
    """
    assert pyperclip is not None

    def restore() -> None:
        try:
            pyperclip.copy(value)
        finally:
            _paste_lock.release()

    if delayed:
        try:
            timer = threading.Timer(_CLIPBOARD_RESTORE_DELAY_SECONDS, restore)
            timer.daemon = True
            timer.start()
            return
        except Exception as e:
            logger.warning(f"Failed to schedule delayed clipboard restore, restoring now: {e}")
    restore()


def restore_focus_and_paste(hwnd: int, original: str, polished: str) -> bool:
    """Replace `original` with `polished` in whatever window `hwnd` refers to.

    Returns True on success. Restores the user's clipboard contents afterward.
    """
    if not _IS_WIN or not hwnd or pyautogui is None or pyperclip is None:
        return False

    # The in-app Alt+Number "Use" shortcut fires on key-down, while Alt may still be
    # physically held - simulating Ctrl+A/C/V before that clears risks it combining
    # into Ctrl+Alt+<key> (see wait_for_keys_released's docstring). A mouse-clicked
    # "Use" holds no key, so this is a no-op there. If Alt is still held once the
    # wait times out, proceeding would risk exactly that corruption, so bail out
    # to the caller's plain-clipboard-copy fallback instead of pasting.
    if not wait_for_keys_released([VK_MENU]):
        logger.warning(
            "Alt still held after timeout - aborting paste-back to avoid corrupting target field"
        )
        return False

    if not _paste_lock.acquire(timeout=_PASTE_LOCK_TIMEOUT_SECONDS):
        logger.warning("Another paste-back is still in progress - aborting")
        return False

    bring_to_foreground(hwnd)
    time.sleep(0.05)
    if ctypes.windll.user32.GetForegroundWindow() != hwnd:  # type: ignore[attr-defined]
        logger.warning("Could not bring original window to foreground for paste-back")
        _paste_lock.release()
        return False

    try:
        original_clipboard = pyperclip.paste()
    except Exception as e:
        logger.warning(f"Failed to read clipboard before paste-back - aborting: {e}")
        _paste_lock.release()
        return False

    paste_sent = False
    try:
        pyperclip.copy("")
        pyautogui.hotkey("ctrl", "a")
        # Give the target app time to finish updating its selection before the
        # copy, same as hotkey.py's select-all capture fallback - firing Ctrl+C
        # immediately risks racing an app that processes the select-all
        # asynchronously, returning stale/incomplete clipboard content.
        time.sleep(SELECT_ALL_SETTLE_SECONDS)
        pyautogui.hotkey("ctrl", "c")
        current = poll_clipboard(timeout=0.4)

        match = _find_normalized(current, original)

        if match is None:
            # Can't verify the originally-selected text is still there unchanged
            # (user edited the field, app auto-reformatted it, or the read above
            # timed out) - abort rather than overwrite the whole field with just
            # the polished text. Caller falls back to a plain clipboard copy.
            logger.warning(
                "Original selection no longer found in the field's live text - "
                "aborting paste-back to avoid overwriting unrelated content"
            )
            if ctypes.windll.user32.GetForegroundWindow() == hwnd:  # type: ignore[attr-defined]
                # The Ctrl+A above left the whole field selected - collapse
                # that selection so a stray keystroke afterward doesn't wipe
                # the field, rather than leaving everything highlighted with
                # no indication the paste-back was aborted.
                pyautogui.press("home")
            return False

        # Splice around the matched span in `current`'s own, unmodified
        # coordinates so any text outside the match - including its original
        # line-ending convention - is preserved exactly, not just the parts
        # normalization happened to leave alone.
        start, end = match
        replacement = current[:start] + polished + current[end:]

        # Focus may have drifted away from hwnd during the read above (another
        # window stealing foreground, a notification, etc.) - re-check right
        # before the destructive select-all+paste rather than trusting the
        # foreground check from ~half a second earlier.
        if ctypes.windll.user32.GetForegroundWindow() != hwnd:  # type: ignore[attr-defined]
            logger.warning("Foreground window changed before paste-back - aborting")
            return False

        pyperclip.copy(replacement)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "v")
        paste_sent = True
        logger.debug("Pasted via clipboard/simulated Ctrl+V")
        return True
    finally:
        _finish_restore(original_clipboard or "", delayed=paste_sent)

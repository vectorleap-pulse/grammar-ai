"""Single-instance guard: only one Grammar AI process may run per user session.

Uses a named mutex to detect an existing instance, and a named event so a
second launch can ask the running instance to show its window before exiting.
"""

import ctypes
import ctypes.wintypes
import sys

from loguru import logger

_IS_WIN = sys.platform == "win32"

_MUTEX_NAME = "GrammarAI_SingleInstanceMutex_8F3A2B1C"
_EVENT_NAME = "GrammarAI_ShowWindowEvent_8F3A2B1C"

_ERROR_ALREADY_EXISTS = 183
_WAIT_OBJECT_0 = 0
_EVENT_MODIFY_STATE = 0x0002

_event_handle: "ctypes.wintypes.HANDLE | None" = None


def acquire_lock() -> bool:
    """Try to become the single running instance.

    Returns True if this process holds the lock and should run normally,
    False if another instance already holds it.
    """
    global _event_handle
    if not _IS_WIN:
        return True

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    kernel32.CreateMutexW.restype = ctypes.wintypes.HANDLE
    kernel32.SetLastError(0)
    kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if ctypes.GetLastError() == _ERROR_ALREADY_EXISTS:
        logger.info("Another Grammar AI instance is already running")
        return False

    kernel32.CreateEventW.restype = ctypes.wintypes.HANDLE
    _event_handle = kernel32.CreateEventW(None, False, False, _EVENT_NAME)
    return True


def signal_existing_instance() -> None:
    """Ask an already-running instance to show its window (called by the loser of acquire_lock)."""
    if not _IS_WIN:
        return

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    kernel32.OpenEventW.restype = ctypes.wintypes.HANDLE
    handle = kernel32.OpenEventW(_EVENT_MODIFY_STATE, False, _EVENT_NAME)
    if handle:
        kernel32.SetEvent(handle)
        kernel32.CloseHandle(handle)
    else:
        logger.warning("Could not signal existing Grammar AI instance to show its window")


def consume_show_signal() -> bool:
    """Non-blocking check: has another launch asked us to show the window?"""
    if not _IS_WIN or _event_handle is None:
        return False
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    return kernel32.WaitForSingleObject(_event_handle, 0) == _WAIT_OBJECT_0

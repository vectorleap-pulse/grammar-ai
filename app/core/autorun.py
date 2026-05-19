import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from app.config import APP_NAME, AUTORUN_REGISTRY_KEY

try:
    import winreg
except ImportError:
    pass

_NUITKA_COMPILED: bool = "__compiled__" in globals()


def _get_current_exe() -> Optional[Path]:
    if not (getattr(sys, "frozen", False) or _NUITKA_COMPILED):
        return None
    return Path(sys.executable)


def configure_autorun(enabled: bool) -> None:
    if sys.platform != "win32":
        return
    exe = _get_current_exe()
    if exe is None:
        return
    try:
        with winreg.OpenKey(  # type: ignore[possibly-undefined]
            winreg.HKEY_CURRENT_USER,
            AUTORUN_REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,  # type: ignore[possibly-undefined]
        ) as key:
            if enabled:
                value = f'"{exe}" --tray-only'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, value)  # type: ignore[possibly-undefined]
                logger.info(f"Autorun enabled: {value}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)  # type: ignore[possibly-undefined]
                    logger.info("Autorun disabled")
                except FileNotFoundError:
                    logger.debug("Autorun registry entry was not present")
    except Exception as e:
        logger.warning(f"Could not configure autorun: {e}")

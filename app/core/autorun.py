import sys

from loguru import logger

_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NAME = "Grammar AI"


def configure_autorun(enabled: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg

    from app.core.updater import get_current_exe

    exe = get_current_exe()
    if exe is None:
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                value = f'"{exe}" --tray-only'
                winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, value)
                logger.info(f"Autorun enabled: {value}")
            else:
                try:
                    winreg.DeleteValue(key, _NAME)
                    logger.info("Autorun disabled")
                except FileNotFoundError:
                    logger.debug("Autorun registry entry was not present")
    except Exception as e:
        logger.warning(f"Could not configure autorun: {e}")

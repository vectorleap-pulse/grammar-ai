import argparse
import importlib.metadata
import sys
import threading
import tomllib
import traceback
from pathlib import Path

from loguru import logger

from app import i18n
from app.config import APP_NAME, DATA_DIR, ERROR_LOG_PATH, ICON_PATH, LOG_PATH, _frozen_base
from app.core import single_instance
from app.core.autorun import configure_autorun
from app.db.database import init_db, load_autorun, load_ui_language

_NUITKA_COMPILED: bool = "__compiled__" in globals()
_WEB_DIR = Path(__file__).resolve().parent / "app" / "ui" / "webview" / "web"


def get_app_version() -> str:
    if getattr(sys, "frozen", False) or _NUITKA_COMPILED:
        try:
            with open(_frozen_base() / "pyproject.toml", "rb") as f:
                data = tomllib.load(f)
            return data["project"]["version"]
        except Exception as e:
            logger.debug(f"Could not read version from pyproject.toml: {e}")
            return "dev"
    try:
        return importlib.metadata.version("grammar-ai")
    except importlib.metadata.PackageNotFoundError:
        pass
    try:
        with open(Path(__file__).resolve().parent / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except Exception as e:
        logger.debug(f"Could not read version from pyproject.toml: {e}")
        return "dev"


def _run_tray(api, window) -> None:
    import pystray
    from PIL import Image

    from app.i18n import Msg, t

    def on_open(*_: object) -> None:
        window.show()
        window.restore()

    def on_quit(*_: object) -> None:
        api.quit_app()

    icon_image = Image.open(ICON_PATH).convert("RGBA")
    menu = pystray.Menu(
        pystray.MenuItem(t(Msg.OPEN), on_open, default=True),
        pystray.MenuItem(t(Msg.QUIT), on_quit),
    )
    icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu)
    api.attach_tray_icon(icon)
    icon.run()


def _run_webview(tray_only: bool) -> None:
    import webview

    from app.ui.webview.api import Api

    api = Api(version=get_app_version())
    window = webview.create_window(
        APP_NAME,
        url=str(_WEB_DIR / "index.html"),
        js_api=api,
        width=340,
        height=708,
        min_size=(340, 548),
        resizable=False,
        hidden=tray_only,
        frameless=True,
        easy_drag=False,
    )
    if window is None:
        raise RuntimeError("pywebview failed to create the main window")

    def _closing() -> bool:
        if load_autorun():
            window.hide()
            return False
        # Don't call api.quit_app() here: it calls window.destroy(), and we're
        # already inside the closing callback that a destroy() call triggered -
        # calling destroy() again while one is in progress is a reentrancy hazard.
        # Returning True lets the in-progress destroy complete on its own.
        api.shutdown()
        return True

    window.events.closing += _closing

    def _on_start() -> None:
        api.attach_window(window)
        threading.Thread(target=_run_tray, args=(api, window), daemon=True).start()

    # private_mode defaults to True in pywebview, which wipes localStorage (and
    # therefore the theme toggle's persisted choice) on every relaunch.
    webview.start(_on_start, debug=False, private_mode=False)


def main() -> None:
    try:
        logger.remove()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(str(LOG_PATH), rotation="10 MB", level="DEBUG", encoding="utf-8")

        if sys.stderr:
            logger.add(sys.stderr, level="WARNING")

        if not single_instance.acquire_lock():
            logger.info("Grammar AI already running - signaling existing instance and exiting")
            single_instance.signal_existing_instance()
            return

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--tray-only", action="store_true")
        args, _ = parser.parse_known_args()

        init_db()
        i18n.set_language(load_ui_language())
        configure_autorun(load_autorun())

        _run_webview(args.tray_only)
    except Exception as e:
        error_msg = f"Error starting Grammar AI: {e}\n{traceback.format_exc()}"
        print(error_msg)

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(ERROR_LOG_PATH, "w") as f:
                f.write(error_msg)
        except Exception as write_err:
            print(f"Could not write error.log: {write_err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

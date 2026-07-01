import ctypes
import importlib
import importlib.metadata
import sys
import threading
import tkinter as tk
import tomllib
import webbrowser
from pathlib import Path
from tkinter import ttk
from typing import Optional

import pystray
from loguru import logger
from PIL import Image, ImageTk

from app.config import (
    APP_NAME,
    ICON_PATH,
    UPDATE_CHECK_INTERVAL_MS,
    WINDOW_GEOMETRY,
    WINDOW_MAX_SIZE,
    WINDOW_MIN_SIZE,
    _frozen_base,
)
from app.core import updater
from app.db.database import load_autorun, load_config
from app.i18n import Msg, t
from app.schemas.models import AppConfig
from app.ui.polish_tab import MainTab
from app.ui.settings_dialog import SettingsDialog
from app.ui.tabs.history_tab import HistoryTab
from app.ui.tooltip import Tooltip
from app.ui.translate_tab import ReadTab

_NUITKA_COMPILED: bool = "__compiled__" in globals()


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
        project_root = Path(__file__).resolve().parents[2]
        with open(project_root / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except Exception as e:
        logger.debug(f"Could not read version from pyproject.toml: {e}")
        return "dev"


class MainWindow(tk.Tk):
    def __init__(self, tray_only: bool = False) -> None:
        super().__init__()
        if tray_only:
            self.withdraw()
        self._version = get_app_version()
        self.title(APP_NAME)
        self.attributes("-alpha", 1.0)
        self.geometry(WINDOW_GEOMETRY)
        self.minsize(*WINDOW_MIN_SIZE)
        self.maxsize(*WINDOW_MAX_SIZE)
        self._set_window_icon()
        self._tray = None
        self._autorun = load_autorun()
        self._config: AppConfig = load_config()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(10, self._remove_maximize_button)
        self.after(5000, self._start_update_check)
        if self._autorun:
            self.after(100, self._start_tray)

    def _build(self) -> None:
        self._update_bar = ttk.Frame(self, padding=(6, 2))
        self._update_lbl = ttk.Label(self._update_bar, font=("", 9))
        self._update_lbl.pack(side="left")
        ttk.Button(self._update_bar, text="✕", width=2, command=self._dismiss_update).pack(
            side="right", padx=(4, 0)
        )
        ttk.Button(
            self._update_bar, text=t(Msg.UPDATE_NOW), command=self._do_update, width=20
        ).pack(side="right")
        self._update_url = ""

        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=4, pady=4)

        self._main_tab = MainTab(self._nb)
        self._read_tab = ReadTab(self._nb)
        self._history_tab = HistoryTab(self._nb)

        self._nb.add(self._main_tab, text=f"  {t(Msg.POLISH)}  ")
        self._nb.add(self._read_tab, text=f"  {t(Msg.TRANSLATE)}  ")
        self._nb.add(self._history_tab, text=f"  {t(Msg.HISTORY)}  ")
        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Floats over the notebook's tab row, top-right, instead of its own row.
        self._tab_toolbar = ttk.Frame(self._nb)
        self._clear_btn = ttk.Button(
            self._tab_toolbar, text="🗑", width=3, command=self._clear_active
        )
        self._clear_btn.pack(side="left", padx=(0, 2))
        Tooltip(self._clear_btn, t(Msg.CLEAR))
        settings_btn = ttk.Button(self._tab_toolbar, text="⚙", width=3, command=self._open_settings)
        settings_btn.pack(side="left")
        Tooltip(settings_btn, t(Msg.SETTINGS))
        self._tab_toolbar.place(in_=self._nb, relx=1.0, x=-3, y=0, anchor="ne")

    def _open_settings(self) -> None:
        SettingsDialog(self, self._config, self._on_config_saved, self.apply_autorun)

    def _on_config_saved(self, config: AppConfig) -> None:
        self._config = config
        self._main_tab.apply_config(config)
        self._read_tab.refresh_translate_language()

    def _clear_active(self) -> None:
        current = self._nb.select()
        if current == str(self._main_tab):
            self._main_tab.clear_all()
        elif current == str(self._read_tab):
            self._read_tab.clear_all()

    def _on_tab_change(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        nb: ttk.Notebook = event.widget  # type: ignore[assignment]
        selected = nb.select()
        if selected == str(self._history_tab):
            self._history_tab.refresh()
        can_clear = selected in (str(self._main_tab), str(self._read_tab))
        self._clear_btn.configure(state="normal" if can_clear else "disabled")

    def _remove_maximize_button(self) -> None:
        if sys.platform != "win32":
            return
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())  # type: ignore[attr-defined]
        GWL_STYLE = -16
        WS_MAXIMIZEBOX = 0x00010000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)  # type: ignore[attr-defined]
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~WS_MAXIMIZEBOX)  # type: ignore[attr-defined]

    def _set_window_icon(self) -> None:
        try:
            self._icon_photo = ImageTk.PhotoImage(Image.open(ICON_PATH))
            self.iconphoto(True, self._icon_photo)  # type: ignore[arg-type]
        except Exception as e:
            logger.debug(f"Could not set window icon: {e}")

    # ------------------------------------------------------------------ tray

    def _start_tray(self) -> None:
        try:
            icon_image = Image.open(ICON_PATH).convert("RGBA")
            menu = pystray.Menu(
                pystray.MenuItem(t(Msg.OPEN), self._tray_open, default=True),
                pystray.MenuItem(t(Msg.QUIT), self._tray_quit),
            )
            self._tray = pystray.Icon(APP_NAME, icon_image, f"{APP_NAME} v{self._version}", menu)
            if self._tray is not None:
                threading.Thread(target=self._tray.run, daemon=True).start()
            else:
                logger.error("Failed to create system tray icon")
        except Exception as ex:
            logger.exception(f"Error occurred while creating system tray icon: {ex}")

    def _tray_open(self, *_: object) -> None:
        self.after(0, self._show_window)

    def _tray_quit(self, *_: object) -> None:
        self.after(0, self._quit)

    def _show_window(self) -> None:
        self.deiconify()
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.attributes("-topmost", False)

    def apply_autorun(self, enabled: bool) -> None:
        self._autorun = enabled
        if enabled and self._tray is None:
            self._start_tray()
        elif not enabled and self._tray is not None:
            try:
                self._tray.stop()
            except Exception as e:
                logger.debug(f"Tray stop error in apply_autorun: {e}")
            self._tray = None

    def _on_close(self) -> None:
        if self._autorun:
            self.withdraw()
        else:
            self._quit()

    def _quit(self) -> None:
        if self._tray is not None:
            try:
                self._tray.stop()
            except Exception as e:
                logger.debug(f"Tray stop error in _quit: {e}")
        self._main_tab.cleanup()
        self._read_tab.cleanup()
        self.destroy()

    # ------------------------------------------------------------------ update

    def _start_update_check(self) -> None:
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self) -> None:
        result = updater.check_for_update(self._version)
        self.after(0, lambda: self._on_update_result(result))

    def _on_update_result(self, result: Optional[tuple]) -> None:
        if result:
            new_version, url = result
            self._update_url = url
            self._update_lbl.config(text=t(Msg.UPDATE_AVAILABLE).format(version=new_version))
            self._update_bar.pack(fill="x", padx=4, pady=(0, 2), before=self._nb)
        else:
            self.after(UPDATE_CHECK_INTERVAL_MS, self._start_update_check)

    def _dismiss_update(self) -> None:
        self._update_bar.pack_forget()
        self.after(UPDATE_CHECK_INTERVAL_MS, self._start_update_check)

    def _do_update(self) -> None:
        if not self._update_url:
            return
        webbrowser.open(self._update_url)

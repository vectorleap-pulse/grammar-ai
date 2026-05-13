import ctypes
import importlib
import importlib.metadata
import sys
import threading
import tkinter as tk
import tomllib
from pathlib import Path
from tkinter import messagebox, ttk
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
)
from app.core import updater
from app.db.database import load_autorun
from app.ui.history_tab import HistoryTab
from app.ui.main_tab import MainTab


def get_app_version() -> str:
    try:
        return importlib.metadata.version("grammar-ai")
    except importlib.metadata.PackageNotFoundError:
        pass

    if getattr(sys, "frozen", False):
        project_root = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        project_root = Path(__file__).resolve().parents[2]

    try:
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
        self.title(f"{APP_NAME} v{self._version}")
        self.attributes("-alpha", 1.0)
        self.geometry(WINDOW_GEOMETRY)
        self.minsize(*WINDOW_MIN_SIZE)
        self.maxsize(*WINDOW_MAX_SIZE)
        self._set_window_icon()
        self._tray = None
        self._autorun = load_autorun()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(10, self._remove_maximize_button)
        updater.cleanup_old_files()
        self.after(5000, self._start_update_check)
        if self._autorun:
            self.after(100, self._start_tray)

    def _build(self) -> None:
        self._update_bar = ttk.Frame(self, padding=(6, 2))
        self._update_lbl = ttk.Label(self._update_bar, font=("", 9))
        self._update_lbl.pack(side="left")
        ttk.Button(self._update_bar, text="Update Now", command=self._do_update, width=20).pack(
            side="right"
        )
        self._update_url = ""

        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=4, pady=4)

        self._main_tab = MainTab(self._nb, on_autorun_change=self.apply_autorun)
        self._history_tab = HistoryTab(self._nb)

        self._nb.add(self._main_tab, text="  Main  ")
        self._nb.add(self._history_tab, text="  History  ")
        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        nb: ttk.Notebook = event.widget  # type: ignore[assignment]
        if nb.tab(nb.select(), "text").strip() == "History":
            self._history_tab.refresh()

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
            self.iconphoto(True, self._icon_photo)
        except Exception as e:
            logger.debug(f"Could not set window icon: {e}")

    # ------------------------------------------------------------------ tray

    def _start_tray(self) -> None:
        try:
            icon_image = Image.open(ICON_PATH).convert("RGBA")
            menu = pystray.Menu(
                pystray.MenuItem("Open", self._tray_open, default=True),
                pystray.MenuItem("Quit", self._tray_quit),
            )
            self._tray = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu)
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
            self._update_lbl.config(text=f"Update v{new_version} available")
            self._update_bar.pack(fill="x", padx=4, pady=(0, 2), before=self._nb)
        else:
            self.after(UPDATE_CHECK_INTERVAL_MS, self._start_update_check)

    def _do_update(self) -> None:
        if not self._update_url:
            return

        dlg_w, dlg_h = 320, 90
        px = self.winfo_x() + (self.winfo_width() - dlg_w) // 2
        py = self.winfo_y() + (self.winfo_height() - dlg_h) // 2

        dlg = tk.Toplevel(self)
        dlg.title("Updating")
        dlg.geometry(f"{dlg_w}x{dlg_h}+{px}+{py}")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text="Downloading update…", font=("", 9)).pack(padx=20, pady=(14, 6))
        progress_var = tk.IntVar(value=0)
        ttk.Progressbar(
            dlg, variable=progress_var, maximum=100, length=280, mode="determinate"
        ).pack(padx=20, pady=(0, 14))

        url = self._update_url

        def on_progress(pct: int) -> None:
            self.after(0, lambda: progress_var.set(pct))

        def worker() -> None:
            new_exe = updater.download_update(url, on_progress=on_progress)
            self.after(0, lambda: _on_done(new_exe))

        def _on_done(new_exe: Optional[Path]) -> None:
            dlg.destroy()
            if new_exe is None:
                messagebox.showerror("Update Failed", "Could not download the update.", parent=self)
                return
            if updater.apply_update(new_exe):
                self._quit()
            else:
                messagebox.showerror("Update Failed", "Could not apply the update.", parent=self)

        threading.Thread(target=worker, daemon=True).start()

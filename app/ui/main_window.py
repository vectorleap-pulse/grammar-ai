import ctypes
import importlib.metadata
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional

from loguru import logger

from app.core import updater
from app.db.database import load_autorun
from app.ui.history_tab import HistoryTab
from app.ui.main_tab import MainTab

_UPDATE_CHECK_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes
_IDLE_OPACITY = 0.3
_IDLE_TIMEOUT_MS = 60 * 1000


def get_app_version() -> str:
    try:
        return importlib.metadata.version("grammar-ai")
    except importlib.metadata.PackageNotFoundError:
        pass

    try:
        import tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]

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


def _make_tray_icon():  # type: ignore[return]
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 2, size - 2], fill=(0, 120, 212, 255))
    draw.text((18, 16), "GA", fill=(255, 255, 255))
    return img


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self._version = get_app_version()
        self.title(f"Grammar AI v{self._version}")
        self.attributes("-alpha", 1.0)
        self.geometry("360x640")
        self.minsize(360, 480)
        self.maxsize(360, 720)
        self._idle_timer_id: Optional[str] = None
        self._tray = None
        self._autorun = load_autorun()
        self._build()
        self._bind_idle_events()
        self._schedule_idle_timer()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(10, self._remove_maximize_button)
        updater.cleanup_old_files()
        self.after(5000, self._start_update_check)
        if self._autorun:
            self.after(100, self._start_tray)

    def _bind_idle_events(self) -> None:
        self.bind_all("<Enter>", self._on_user_activity)
        self.bind_all("<Motion>", self._on_user_activity)
        self.bind_all("<Button>", self._on_user_activity)
        self.bind_all("<Key>", self._on_user_activity)
        self.bind_all("<FocusIn>", self._on_user_activity)

    def _schedule_idle_timer(self) -> None:
        if self._idle_timer_id is not None:
            self.after_cancel(self._idle_timer_id)
        self._idle_timer_id = self.after(_IDLE_TIMEOUT_MS, self._on_idle_timeout)

    def _on_idle_timeout(self) -> None:
        self._idle_timer_id = None
        try:
            self.attributes("-alpha", _IDLE_OPACITY)
        except tk.TclError:
            pass

    def _on_user_activity(self, event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        try:
            self.attributes("-alpha", 1.0)
        except tk.TclError:
            pass
        self._schedule_idle_timer()

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

    # ------------------------------------------------------------------ tray

    def _start_tray(self) -> None:
        try:
            import pystray

            icon_image = _make_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem("Open", self._tray_open, default=True),
                pystray.MenuItem("Quit", self._tray_quit),
            )
            self._tray = pystray.Icon("Grammar AI", icon_image, "Grammar AI", menu)
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
        self._on_user_activity()

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
            self.after(_UPDATE_CHECK_INTERVAL_MS, self._start_update_check)

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

import ctypes
import importlib.metadata
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from app.ui.history_tab import HistoryTab
from app.ui.main_tab import MainTab


def get_app_version() -> str:
    """Get the application version from installed metadata or pyproject.toml."""
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
    except Exception:
        return "dev"


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        version = get_app_version()
        self.title(f"Grammar AI v{version}")
        self.attributes("-topmost", True)
        self.geometry("400x680")
        self.minsize(400, 520)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(10, self._remove_maximize_button)

    def _build(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        self._main_tab = MainTab(nb)
        self._history_tab = HistoryTab(nb)

        nb.add(self._main_tab, text="  Main  ")
        nb.add(self._history_tab, text="  History  ")

        nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

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

    def _on_close(self) -> None:
        self._main_tab.cleanup()
        self.destroy()

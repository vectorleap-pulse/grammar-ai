import tkinter as tk
from tkinter import ttk

from app.ui.history_tab import HistoryTab
from app.ui.main_tab import MainTab


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Grammar AI")
        self.attributes("-topmost", True)
        self.geometry("400x680")
        self.minsize(400, 520)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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

    def _on_close(self) -> None:
        self._main_tab.cleanup()
        self.destroy()

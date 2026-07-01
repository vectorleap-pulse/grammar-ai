import tkinter as tk
from typing import Optional


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._tip: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        x = self._widget.winfo_rootx() + 20
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 2
        self._tip = tk.Toplevel(self._widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._tip,
            text=self._text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("", 8),
            padx=4,
            pady=2,
        ).pack()

    def _hide(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._tip:
            self._tip.destroy()
            self._tip = None

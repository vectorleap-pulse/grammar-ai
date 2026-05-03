import tkinter as tk
from tkinter import ttk

from app.db.database import load_history


class HistoryTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self._build()
        self.refresh()

    def _build(self) -> None:
        bar = ttk.Frame(self, padding=(6, 4))
        bar.pack(fill="x")
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left")

        cols = ("used_at", "tone", "polished_text", "original_text")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")

        self._tree.heading("used_at", text="Used At")
        self._tree.heading("tone", text="Tone")
        self._tree.heading("polished_text", text="Polished Text")
        self._tree.heading("original_text", text="Original")

        self._tree.column("used_at", width=130, stretch=False)
        self._tree.column("tone", width=90, stretch=False)
        self._tree.column("polished_text", width=320)
        self._tree.column("original_text", width=180)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=(0, 6))
        vsb.pack(side="right", fill="y", pady=(0, 6), padx=(0, 6))

        # Show full text of selected row in a detail label.
        self._detail_var = tk.StringVar()
        detail = ttk.Label(
            self, textvariable=self._detail_var, wraplength=700,
            justify="left", font=("", 9), anchor="w",
        )
        detail.pack(fill="x", padx=6, pady=(0, 4))
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def refresh(self) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        self._detail_var.set("")
        for e in load_history():
            self._tree.insert(
                "", "end",
                iid=str(e.id),
                values=(
                    e.used_at.strftime("%Y-%m-%d %H:%M"),
                    e.tone,
                    e.polished_text[:120],
                    e.original_text[:60],
                ),
                tags=(e.polished_text,),
            )

    def _on_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if not sel:
            return
        tags = self._tree.item(sel[0], "tags")
        if tags:
            self._detail_var.set(tags[0])

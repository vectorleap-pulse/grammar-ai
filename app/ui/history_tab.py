import tkinter as tk
from tkinter import ttk

from app.db.database import clear_history, get_history_count, load_history


class HistoryTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.current_page = 0
        self.page_size = 50
        self._build()
        self.refresh()

    def _build(self) -> None:
        bar = ttk.Frame(self, padding=(6, 4))
        bar.pack(fill="x")
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="left", padx=(4, 0))

        # Pagination controls
        pagination_frame = ttk.Frame(self, padding=(6, 4))
        pagination_frame.pack(fill="x")

        ttk.Label(pagination_frame, text="Page size:").pack(side="left")
        self.page_size_var = tk.StringVar(value=str(self.page_size))
        page_size_combo = ttk.Combobox(
            pagination_frame,
            textvariable=self.page_size_var,
            values=["10", "25", "50", "100"],
            width=5,
        )
        page_size_combo.pack(side="left", padx=(4, 0))
        page_size_combo.bind("<<ComboboxSelected>>", self._on_page_size_change)

        ttk.Button(pagination_frame, text="Prev", command=self.prev_page).pack(
            side="left", padx=(10, 0)
        )
        self.page_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_label.pack(side="left", padx=(4, 0))
        ttk.Button(pagination_frame, text="Next", command=self.next_page).pack(
            side="left", padx=(4, 0)
        )

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
            self,
            textvariable=self._detail_var,
            wraplength=700,
            justify="left",
            font=("", 9),
            anchor="w",
        )
        detail.pack(fill="x", padx=6, pady=(0, 4))
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def refresh(self) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        self._detail_var.set("")
        offset = self.current_page * self.page_size
        for e in load_history(limit=self.page_size, offset=offset):
            self._tree.insert(
                "",
                "end",
                iid=str(e.id),
                values=(
                    e.used_at.strftime("%Y-%m-%d %H:%M"),
                    e.tone,
                    e.polished_text[:120],
                    e.original_text[:60],
                ),
                tags=(e.polished_text,),
            )
        self._update_page_label()

    def _on_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        sel = self._tree.selection()
        if not sel:
            return
        tags = self._tree.item(sel[0], "tags")
        if tags:
            self._detail_var.set(tags[0])

    def clear(self) -> None:
        clear_history()
        self.current_page = 0
        self.refresh()

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh()

    def next_page(self) -> None:
        total_count = get_history_count()
        max_page = (total_count - 1) // self.page_size
        if self.current_page < max_page:
            self.current_page += 1
            self.refresh()

    def _on_page_size_change(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        try:
            new_size = int(self.page_size_var.get())
            if new_size > 0:
                self.page_size = new_size
                self.current_page = 0
                self.refresh()
        except ValueError:
            pass

    def _update_page_label(self) -> None:
        total_count = get_history_count()
        total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        self.page_label.config(text=f"Page {self.current_page + 1} of {total_pages}")

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

        cols = ("used_at", "tone", "polished_text")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")

        self._tree.heading("used_at", text="Used At")
        self._tree.heading("tone", text="Tone")
        self._tree.heading("polished_text", text="Polished Text")

        self._tree.column("used_at", width=130, stretch=False)
        self._tree.column("tone", width=90, stretch=False)
        self._tree.column("polished_text", width=150, minwidth=80, stretch=True)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=(0, 6))
        vsb.pack(side="right", fill="y", pady=(0, 6), padx=(0, 6))
        self._tree.bind("<Double-1>", self._on_double_click)

    def refresh(self) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        offset = self.current_page * self.page_size
        for e in load_history(limit=self.page_size, offset=offset):
            first_line = e.polished_text.split("\n")[0][:120]  # Show only first line, truncated
            self._tree.insert(
                "",
                "end",
                iid=str(e.id),
                values=(
                    e.used_at.strftime("%Y-%m-%d %H:%M"),
                    e.tone,
                    first_line,
                ),
                tags=(e.polished_text, e.original_text),  # Keep both in tags for detail view
            )
        self._update_page_label()

    def _on_double_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        item = self._tree.identify_row(event.y)
        if not item:
            return
        tags = self._tree.item(item, "tags")
        if not tags or len(tags) < 2:
            return
        polished, original = tags[0], tags[1]
        values = self._tree.item(item, "values")
        used_at, tone = values[0], values[1]

        parent = self.winfo_toplevel()
        dlg_w, dlg_h = 480, 500
        px = parent.winfo_x() + (parent.winfo_width() - dlg_w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - dlg_h) // 2

        dlg = tk.Toplevel(self)
        dlg.title("History Entry")
        dlg.geometry(f"{dlg_w}x{dlg_h}+{px}+{py}")
        dlg.resizable(True, True)
        dlg.transient(parent)
        dlg.grab_set()

        meta = ttk.Frame(dlg)
        meta.pack(fill="x", padx=8, pady=(8, 4))
        for label, value in [("ID", item), ("Tone", tone), ("Used At", used_at)]:
            row = ttk.Frame(meta)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=f"{label}:", font=("", 9, "bold"), width=8, anchor="w").pack(side="left")
            ttk.Label(row, text=value, font=("", 9)).pack(side="left")

        ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=8, pady=4)

        for label, content in [("Original Text", original), ("Polished Text", polished)]:
            ttk.Label(dlg, text=label, font=("", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 2))
            frame = ttk.Frame(dlg)
            frame.pack(fill="both", expand=True, padx=8)
            txt = tk.Text(frame, wrap="word", font=("", 9), height=6)
            vsb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vsb.set)
            txt.insert("1.0", content)
            txt.config(state="disabled")
            vsb.pack(side="right", fill="y")
            txt.pack(side="left", fill="both", expand=True)

        ttk.Button(dlg, text="Close", command=dlg.destroy).pack(pady=8)

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

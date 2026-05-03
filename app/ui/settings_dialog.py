import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from loguru import logger

from app.core.llm import check_connection
from app.db.database import save_config
from app.schemas.models import LLMConfig


class SettingsDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        config: LLMConfig,
        on_save: Callable[[LLMConfig], None],
    ) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self._on_save = on_save
        self._build()
        self._load(config)

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}
        f = ttk.Frame(self, padding=12)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Base URL:").grid(row=0, column=0, sticky="w", **pad)
        self._url = ttk.Entry(f, width=44)
        self._url.grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(f, text="Model:").grid(row=1, column=0, sticky="w", **pad)
        self._model = ttk.Entry(f, width=44)
        self._model.grid(row=1, column=1, sticky="ew", **pad)

        ttk.Label(f, text="API Key:").grid(row=2, column=0, sticky="w", **pad)
        self._key = ttk.Entry(f, width=44, show="*")
        self._key.grid(row=2, column=1, sticky="ew", **pad)

        self._status = ttk.Label(f, text="", foreground="gray", font=("", 8))
        self._status.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=2)

        btn_row = ttk.Frame(f)
        btn_row.grid(row=4, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btn_row, text="Test Connection", command=self._test).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        f.columnconfigure(1, weight=1)

    def _load(self, config: LLMConfig) -> None:
        self._url.delete(0, "end")
        self._url.insert(0, config.base_url)
        self._model.delete(0, "end")
        self._model.insert(0, config.model)
        self._key.delete(0, "end")
        self._key.insert(0, config.api_key)

    def _current(self) -> LLMConfig:
        return LLMConfig(
            base_url=self._url.get().strip(),
            model=self._model.get().strip(),
            api_key=self._key.get().strip(),
        )

    def _test(self) -> None:
        self._status.config(text="Testing…", foreground="gray")
        self.update_idletasks()
        ok, msg = check_connection(self._current())
        self._status.config(text=msg, foreground="green" if ok else "red")
        logger.info(f"Config test result: {ok} — {msg}")

    def _save(self) -> None:
        cfg = self._current()
        if not cfg.api_key:
            messagebox.showwarning("Missing field", "API key is required.", parent=self)
            return
        if not cfg.model:
            messagebox.showwarning("Missing field", "Model name is required.", parent=self)
            return
        save_config(cfg)
        self._on_save(cfg)
        logger.info("Settings saved and applied")
        self.destroy()

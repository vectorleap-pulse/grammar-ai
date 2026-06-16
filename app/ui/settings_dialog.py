import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from loguru import logger

from app.config import (
    GOAL_DESCRIPTIONS,
    GOALS,
    GOALS_PRESET_DEFAULT,
    GOALS_PRESET_MIN,
    OUTPUT_LANGUAGES,
    UI_LANGUAGES,
)
from app.core.autorun import configure_autorun
from app.core.llm import check_connection
from app.db.database import (
    load_autorun,
    load_selected_goals,
    load_ui_language,
    save_autorun,
    save_config,
    save_selected_goals,
    save_ui_language,
)
from app.i18n import Msg, goal_name, t
from app.schemas.models import Goal, LLMConfig


class _Tooltip:
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


class SettingsDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        config: LLMConfig,
        on_save: Callable[[LLMConfig], None],
        on_autorun_change: Optional[Callable[[bool], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.title("Settings")
        self.resizable(False, False)
        self.transient(parent)  # type: ignore
        self._on_save = on_save
        self._on_autorun_change = on_autorun_change
        self._build()
        self._load(config)
        self.update_idletasks()
        self._center(parent)
        self.deiconify()
        self.grab_set()

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}
        f = ttk.Frame(self, padding=12)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text=t(Msg.BASE_URL)).grid(row=0, column=0, sticky="w", **pad)  # type:ignore
        self._url = ttk.Entry(f, width=44)
        self._url.grid(row=0, column=1, sticky="ew", **pad)  # type: ignore

        ttk.Label(f, text=t(Msg.MODEL)).grid(row=1, column=0, sticky="w", **pad)  # type: ignore
        self._model = ttk.Entry(f, width=44)
        self._model.grid(row=1, column=1, sticky="ew", **pad)  # type: ignore

        ttk.Label(f, text=t(Msg.API_KEY)).grid(row=2, column=0, sticky="w", **pad)  # type: ignore
        self._key = ttk.Entry(f, width=44, show="*")
        self._key.grid(row=2, column=1, sticky="ew", **pad)  # type: ignore

        ttk.Label(f, text=t(Msg.OUTPUT_LANGUAGE)).grid(row=3, column=0, sticky="w", **pad)  # type: ignore
        self._language = ttk.Combobox(f, width=42, values=list(OUTPUT_LANGUAGES.keys()))
        self._language.grid(row=3, column=1, sticky="ew", **pad)  # type: ignore
        self._tooltips_misc = _Tooltip(self._language, t(Msg.OUTPUT_LANGUAGE_TOOLTIP))

        ttk.Label(f, text=t(Msg.INTERFACE_LANGUAGE)).grid(row=4, column=0, sticky="w", **pad)  # type: ignore
        self._ui_language = ttk.Combobox(
            f, width=42, values=list(UI_LANGUAGES.keys()), state="readonly"
        )
        self._ui_language.grid(row=4, column=1, sticky="ew", **pad)  # type: ignore

        self._autorun_var = tk.BooleanVar(value=load_autorun())
        ttk.Checkbutton(f, text=t(Msg.RUN_AT_STARTUP), variable=self._autorun_var).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=8, pady=4
        )

        # Goal selection
        goals_lf = ttk.LabelFrame(f, text=t(Msg.GOALS_TO_GENERATE), padding=(8, 4))
        goals_lf.grid(row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 0))

        preset_row = ttk.Frame(goals_lf)
        preset_row.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Button(
            preset_row,
            text=t(Msg.MINIMUM),
            width=9,
            command=lambda: self._set_goals(GOALS_PRESET_MIN),
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            preset_row,
            text=t(Msg.DEFAULT),
            width=9,
            command=lambda: self._set_goals(GOALS_PRESET_DEFAULT),
        ).pack(side="left", padx=4)
        ttk.Button(preset_row, text=t(Msg.ALL), width=9, command=lambda: self._set_goals(GOALS)).pack(
            side="left", padx=4
        )

        saved_goals = load_selected_goals()
        self._goal_vars: dict[Goal, tk.BooleanVar] = {}
        self._tooltips: list[_Tooltip] = []
        for i, goal in enumerate(GOALS):
            var = tk.BooleanVar(value=goal in saved_goals)
            self._goal_vars[goal] = var
            cb = ttk.Checkbutton(goals_lf, text=goal_name(goal), variable=var)
            cb.grid(row=(i // 3) + 1, column=i % 3, sticky="w", padx=6, pady=2)
            if goal in GOAL_DESCRIPTIONS:
                self._tooltips.append(_Tooltip(cb, GOAL_DESCRIPTIONS[goal]))

        disclaimer_row = (len(GOALS) - 1) // 3 + 2
        ttk.Label(
            goals_lf,
            text=t(Msg.MORE_GOALS_DISCLAIMER),
            foreground="gray",
            font=("", 8, "italic"),
        ).grid(row=disclaimer_row, column=0, columnspan=3, sticky="w", padx=6, pady=(4, 2))

        # Advanced section
        adv_lf = ttk.LabelFrame(f, text=t(Msg.ADVANCED), padding=(8, 4))
        adv_lf.grid(row=7, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 0))
        adv_lf.columnconfigure(0, weight=1)

        self._use_default_prompt_var = tk.BooleanVar(value=True)
        cb_default_prompt = ttk.Checkbutton(
            adv_lf,
            text=t(Msg.USE_DEFAULT_PROMPT),
            variable=self._use_default_prompt_var,
            command=self._toggle_custom_prompt,
        )
        cb_default_prompt.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self._custom_prompt_frame = ttk.Frame(adv_lf)

        ttk.Label(self._custom_prompt_frame, text=t(Msg.CUSTOM_PROMPT)).pack(anchor="w")
        text_frame = ttk.Frame(self._custom_prompt_frame)
        text_frame.pack(fill="both", expand=True, pady=(2, 0))

        self._custom_prompt_text = tk.Text(
            text_frame, height=5, width=44, font=("", 9), wrap="word"
        )
        scroll = ttk.Scrollbar(
            text_frame, orient="vertical", command=self._custom_prompt_text.yview
        )
        self._custom_prompt_text.configure(yscrollcommand=scroll.set)

        self._custom_prompt_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._status = ttk.Label(f, text="", foreground="gray", font=("", 8), wraplength=400)
        self._status.grid(row=8, column=0, columnspan=2, sticky="w", padx=8, pady=2)

        btn_row = ttk.Frame(f)
        btn_row.grid(row=9, column=0, columnspan=2, pady=(8, 0))
        ttk.Button(btn_row, text=t(Msg.TEST_CONNECTION), command=self._test).pack(side="left", padx=4)
        ttk.Button(btn_row, text=t(Msg.SAVE), command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_row, text=t(Msg.CANCEL), command=self.destroy).pack(side="left", padx=4)

        f.columnconfigure(1, weight=1)

    def _toggle_custom_prompt(self) -> None:
        if self._use_default_prompt_var.get():
            self._custom_prompt_frame.grid_remove()
        else:
            self._custom_prompt_frame.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        # Force the window to recalculate its minimum size based on current content
        self.update_idletasks()

        new_width = self.winfo_reqwidth()
        new_height = self.winfo_reqheight()

        self.geometry(f"{new_width}x{new_height}")

    def _load(self, config: LLMConfig) -> None:
        self._url.delete(0, "end")
        self._url.insert(0, config.base_url)
        self._model.delete(0, "end")
        self._model.insert(0, config.model)
        self._key.delete(0, "end")
        self._key.insert(0, config.api_key)
        # Show the friendly label (e.g. "Korean (한국어)") for the stored language value.
        value = config.output_language or "English"
        out_label = {v: k for k, v in OUTPUT_LANGUAGES.items()}
        self._language.set(out_label.get(value, value))

        self._initial_ui_lang = load_ui_language()
        code_to_label = {code: label for label, code in UI_LANGUAGES.items()}
        self._ui_language.set(code_to_label.get(self._initial_ui_lang, "English"))

        self._use_default_prompt_var.set(config.use_default_prompt)
        self._custom_prompt_text.delete("1.0", "end")
        if config.custom_prompt:
            self._custom_prompt_text.insert("1.0", config.custom_prompt)
        self._toggle_custom_prompt()

    def _current(self) -> LLMConfig:
        # Map the friendly label back to the plain language value sent to the model;
        # free-typed custom languages pass through unchanged.
        label = self._language.get().strip()
        output_language = OUTPUT_LANGUAGES.get(label, label) or "English"
        return LLMConfig(
            base_url=self._url.get().strip(),
            model=self._model.get().strip(),
            api_key=self._key.get().strip(),
            output_language=output_language,
            use_default_prompt=self._use_default_prompt_var.get(),
            custom_prompt=self._custom_prompt_text.get("1.0", "end-1c").strip(),
        )

    def _set_goals(self, preset: list[Goal]) -> None:
        for goal, var in self._goal_vars.items():
            var.set(goal in preset)

    def _selected_goals(self) -> list[Goal]:
        return [g for g in GOALS if self._goal_vars[g].get()]

    def _test(self) -> None:
        self._status.config(text=t(Msg.TESTING), foreground="gray")
        self.update_idletasks()
        ok, msg = check_connection(self._current())
        self._status.config(text=msg, foreground="green" if ok else "red")
        logger.info(f"Config test result: {ok} — {msg}")

    def _save(self) -> None:
        cfg = self._current()
        if not cfg.api_key:
            messagebox.showwarning(t(Msg.MISSING_FIELD), t(Msg.API_KEY_REQUIRED), parent=self)
            return
        if not cfg.model:
            messagebox.showwarning(t(Msg.MISSING_FIELD), t(Msg.MODEL_REQUIRED), parent=self)
            return

        goals = self._selected_goals()
        if not goals:
            messagebox.showwarning(
                t(Msg.NO_GOALS_SELECTED), t(Msg.SELECT_AT_LEAST_ONE_GOAL), parent=self
            )
            return

        save_config(cfg)
        save_selected_goals(goals)
        self._on_save(cfg)

        autorun = self._autorun_var.get()
        save_autorun(autorun)
        configure_autorun(autorun)
        if self._on_autorun_change:
            self._on_autorun_change(autorun)

        ui_lang = UI_LANGUAGES.get(self._ui_language.get(), "en")
        save_ui_language(ui_lang)
        ui_lang_changed = ui_lang != self._initial_ui_lang

        logger.info("Settings saved and applied")
        self.destroy()

        if ui_lang_changed:
            messagebox.showinfo(
                t(Msg.SETTINGS),
                t(Msg.RESTART_TO_APPLY_LANGUAGE),
                parent=self.master,
            )

    def _center(self, parent: tk.Widget) -> None:
        parent_win = parent.winfo_toplevel()

        pw = parent_win.winfo_width()
        ph = parent_win.winfo_height()
        px = parent_win.winfo_x()
        py = parent_win.winfo_y()

        sw = self.winfo_reqwidth()
        sh = self.winfo_reqheight()

        x = px + (pw - sw) // 2
        y = py + (ph - sh) // 2
        self.geometry(f"{sw}x{sh}+{x}+{y}")

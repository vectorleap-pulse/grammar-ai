import threading
import tkinter as tk
from tkinter import messagebox, ttk

import pyperclip
from loguru import logger

from app.config import OUTPUT_LANGUAGES, TRANSLATE_HOTKEYS
from app.core.hotkey import _HOTKEY_ID_TRANSLATE, MOD_CONTROL, MOD_SHIFT, VK_SPACE, HotkeyManager
from app.core.llm import translate_text
from app.db.database import load_config, load_translate_language
from app.i18n import Msg, t


class TranslateTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        hotkey_desc = "+".join(h.capitalize() for h in TRANSLATE_HOTKEYS)
        self._hotkey = HotkeyManager(
            self._on_hotkey_text,
            modifiers=MOD_CONTROL | MOD_SHIFT,
            vk=VK_SPACE,
            hotkey_id=_HOTKEY_ID_TRANSLATE,
            description=hotkey_desc,
        )
        self._build()
        self._hotkey.enable()

    def _build(self) -> None:
        self._build_original()
        self._build_action_bar()
        self._build_output()

    def _build_original(self) -> None:
        lf = ttk.LabelFrame(self, text=t(Msg.ORIGINAL_TEXT), padding=4)
        lf.pack(fill="x", padx=6, pady=(6, 4))
        self._orig = tk.Text(lf, height=5, wrap="word", font=("", 9))
        self._orig.pack(fill="x")

    def _build_action_bar(self) -> None:
        btn_row = ttk.Frame(self, padding=(6, 2))
        btn_row.pack(fill="x")

        hotkey = "+".join(h.capitalize() for h in TRANSLATE_HOTKEYS)
        self._translate_btn = ttk.Button(
            btn_row,
            text=t(Msg.TRANSLATE_ACTION) + f" ({hotkey})",
            command=self._trigger_manual,
        )
        self._translate_btn.pack(side="left", padx=2)

        self._status_var = tk.StringVar(value="")
        self._status_lbl = ttk.Label(btn_row, textvariable=self._status_var, font=("", 8))
        self._status_lbl.pack(side="left", padx=(6, 0))

    def _output_title(self) -> str:
        return t(Msg.TRANSLATED_TEXT) + ": " + load_translate_language()

    def _build_output(self) -> None:
        self._output_lf = ttk.LabelFrame(self, text=self._output_title(), padding=4)
        lf = self._output_lf
        lf.pack(fill="both", expand=True, padx=6, pady=(6, 4))

        self._output = tk.Text(
            lf,
            wrap="word",
            font=("", 9),
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
        )
        vsb = ttk.Scrollbar(lf, orient="vertical", command=self._output.yview)
        self._output.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._output.pack(side="left", fill="both", expand=True)

        copy_row = ttk.Frame(self, padding=(6, 0, 6, 6))
        copy_row.pack(fill="x")
        self._copy_btn = ttk.Button(
            copy_row, text=t(Msg.COPY), command=self._copy, state="disabled"
        )
        self._copy_btn.pack(side="right")

    # ------------------------------------------------------------------ hotkey

    def _on_hotkey_text(self, text: str) -> None:
        self.after(0, lambda: self._handle_hotkey_result(text))

    def _handle_hotkey_result(self, text: str) -> None:
        nb = self.master
        if isinstance(nb, ttk.Notebook):
            nb.select(self)
        self._orig.delete("1.0", "end")
        self._orig.insert("1.0", text)
        self._run_translate(text)
        top = self.winfo_toplevel()
        if hasattr(top, "_show_window"):
            top._show_window()  # type: ignore[union-attr]
        else:
            top.deiconify()
            top.lift()
            top.focus_force()

    # ------------------------------------------------------------------ trigger

    def _trigger_manual(self) -> None:
        text = self._orig.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo(
                t(Msg.EMPTY),
                t(Msg.ENTER_TEXT_TO_TRANSLATE),
                parent=self.winfo_toplevel(),
            )
            return
        self._run_translate(text)

    # ------------------------------------------------------------------ LLM

    def _run_translate(self, text: str) -> None:
        if str(self._translate_btn.cget("state")) == "disabled":
            return

        config = load_config()
        if not config.api_key:
            messagebox.showwarning(
                t(Msg.NO_API_KEY),
                t(Msg.CONFIGURE_API_KEY),
                parent=self.winfo_toplevel(),
            )
            return

        self._translate_btn.configure(state="disabled")
        self._copy_btn.configure(state="disabled")
        self._set_output("")
        self._set_status(t(Msg.TRANSLATING), "blue")

        lang_label = load_translate_language()
        lang = OUTPUT_LANGUAGES.get(lang_label, lang_label)

        def worker() -> None:
            try:
                result = translate_text(text, lang, config)
                logger.info(f"Translation complete ({lang}), {len(result)} chars")
                self.after(0, lambda: self._on_done(result))
            except Exception as exc:
                error_msg = str(exc)
                logger.error(f"Translation error: {error_msg}")
                self.after(0, lambda: self._on_error(error_msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, result: str) -> None:
        self._set_output(result)
        self._set_status(t(Msg.TRANSLATION_READY), "green")
        self._translate_btn.configure(state="normal")
        self._copy_btn.configure(state="normal")

    def _on_error(self, error_msg: str) -> None:
        self._set_status(t(Msg.ERROR), "red")
        self._translate_btn.configure(state="normal")
        messagebox.showerror(t(Msg.LLM_ERROR), error_msg, parent=self.winfo_toplevel())

    # ------------------------------------------------------------------ helpers

    def refresh_translate_language(self) -> None:
        self._output_lf.config(text=self._output_title())

    def clear_all(self) -> None:
        self._orig.delete("1.0", "end")
        self._set_output("")
        self._set_status("", "gray")
        self._copy_btn.configure(state="disabled")

    def _set_output(self, text: str) -> None:
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        if text:
            self._output.insert("1.0", text)
        self._output.configure(state="disabled")

    def _set_status(self, msg: str, color: str = "gray") -> None:
        self._status_var.set(msg)
        self._status_lbl.configure(foreground=color)

    def _copy(self) -> None:
        text = self._output.get("1.0", "end-1c")
        if text:
            pyperclip.copy(text)
            self._copy_btn.configure(text=t(Msg.COPIED_EXCL))
            self.after(1500, lambda: self._copy_btn.configure(text=t(Msg.COPY)))

    def cleanup(self) -> None:
        self._hotkey.disable()

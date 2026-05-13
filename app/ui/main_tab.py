import os
import threading
import tkinter as tk
import tkinter.font as tkFont
from tkinter import messagebox, ttk
from typing import Callable, Optional

import pyperclip
from loguru import logger

from app.core.focus import restore_focus_and_paste
from app.core.hotkey import HOTKEY, HotkeyManager
from app.core.llm import TONES, polish_text
from app.db.database import LOG_PATH, load_config, save_history
from app.schemas.models import LLMConfig, PolishedText


class _PolishedItem(ttk.Frame):
    """One polished-text card: tone badge + editable text + Use button."""

    def __init__(
        self,
        parent: tk.Widget,
        tone: str,
        text: str,
        on_use: Callable[[str, str], None],
    ) -> None:
        super().__init__(parent, relief="groove", borderwidth=1)
        self._tone = tone
        self._on_use = on_use
        self._build(tone, text)

    def _build(self, tone: str, text: str) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", padx=4, pady=(4, 0))
        ttk.Label(header, text=tone.capitalize(), font=("", 8, "bold")).pack(side="left")
        ttk.Button(header, text="Use", width=5, command=self._use).pack(side="right")

        self._txt = tk.Text(
            self, wrap="word", font=("", 9), borderwidth=0, highlightthickness=0, relief="flat"
        )
        self._txt.insert("1.0", text)
        self._txt.pack(fill="both", expand=True, padx=4, pady=(2, 4))
        # Schedule height update after rendering
        self.after(10, self._update_height)

    def _update_height(self) -> None:
        self._txt.update_idletasks()

        # Get font metrics
        font = tkFont.Font(font=self._txt.cget("font"))
        _line_height = font.metrics("linespace")

        # Get parent frame width to calculate word wrap
        parent_width = self.winfo_width() - 8  # Account for padding
        if parent_width < 1:
            self.after(10, self._update_height)
            return

        # Calculate char width for this font
        char_width = font.measure("0")
        chars_per_line = max(1, parent_width // char_width)

        # Count lines with word wrapping
        content = self._txt.get("1.0", "end-1c")
        total_display_lines = 0
        for logical_line in content.split("\n"):
            if not logical_line:
                total_display_lines += 1
            else:
                # Calculate wrapped lines for this logical line
                wrapped = max(1, (len(logical_line) + chars_per_line - 1) // chars_per_line)
                total_display_lines += wrapped

        height = max(3, total_display_lines)
        self._txt.config(height=height)

    def get_text(self) -> str:
        return self._txt.get("1.0", "end-1c")

    def _use(self) -> None:
        self._on_use(self._tone, self.get_text())


class MainTab(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        on_autorun_change: Optional[Callable[[bool], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._config: LLMConfig = load_config()
        self._hotkey = HotkeyManager(self._on_hotkey_text)
        self._items: list[_PolishedItem] = []
        self._received = 0
        self._on_autorun_change = on_autorun_change
        self._build()
        self._hotkey.enable()

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        self._build_toolbar()
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=4)
        self._build_original()
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=4)
        self._build_results()

    def _build_toolbar(self) -> None:
        # First line: Clear and Settings buttons
        bar1 = ttk.Frame(self, padding=(6, 4))
        bar1.pack(fill="x")

        ttk.Button(bar1, text="Clear", command=self._clear_all).pack(side="left", padx=2)
        ttk.Button(bar1, text="Settings", command=self._open_settings).pack(side="right", padx=2)

        # Second line: Trigger button and status message
        bar2 = ttk.Frame(self, padding=(6, 4))
        bar2.pack(fill="x")

        ttk.Button(bar2, text=f"Trigger ({HOTKEY.upper()})", command=self._trigger_manual).pack(
            side="left", padx=2
        )

        self._status_var = tk.StringVar(value="")
        self._status_lbl = ttk.Label(bar2, textvariable=self._status_var, font=("", 8))
        self._status_lbl.pack(side="left", padx=8)

    def _build_original(self) -> None:
        lf = ttk.LabelFrame(self, text="Original Text", padding=4)
        lf.pack(fill="x", padx=6, pady=4)

        self._orig = tk.Text(lf, height=4, wrap="word", font=("", 9))
        self._orig.pack(fill="x")
        self._orig.bind("<KeyRelease>", lambda e: self._update_original_height())
        # Schedule initial height update after rendering
        self.after(10, self._update_original_height)

    def _build_results(self) -> None:
        lf = ttk.LabelFrame(self, text="Polished Versions", padding=4)
        lf.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        canvas = tk.Canvas(lf, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(lf, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._results_frame = ttk.Frame(canvas)
        self._cw = canvas.create_window((0, 0), window=self._results_frame, anchor="nw")

        self._results_frame.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self._cw, width=e.width),
        )
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self._canvas = canvas

    def _update_original_height(self) -> None:
        self._orig.update_idletasks()

        # Get font metrics
        font = tkFont.Font(font=self._orig.cget("font"))
        _line_height = font.metrics("linespace")

        # Get parent frame width to calculate word wrap
        parent_width = self._orig.winfo_width()
        if parent_width < 1:
            self.after(10, self._update_original_height)
            return

        # Calculate char width for this font
        char_width = font.measure("0")
        chars_per_line = max(1, parent_width // char_width)

        # Count lines with word wrapping
        content = self._orig.get("1.0", "end-1c")
        total_display_lines = 0
        for logical_line in content.split("\n"):
            if not logical_line:
                total_display_lines += 1
            else:
                # Calculate wrapped lines for this logical line
                wrapped = max(1, (len(logical_line) + chars_per_line - 1) // chars_per_line)
                total_display_lines += wrapped

        height = max(3, min(6, total_display_lines))
        self._orig.config(height=height)

    # ------------------------------------------------------------------ settings

    def _open_settings(self) -> None:
        from app.ui.settings_dialog import SettingsDialog

        SettingsDialog(self, self._config, self._on_config_saved, self._on_autorun_change)

    def _on_config_saved(self, config: LLMConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------ trigger

    def _trigger_manual(self) -> None:
        text = self._orig.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo(
                "Empty",
                "Enter or paste text to polish.",
                parent=self.winfo_toplevel(),
            )
            return
        self._run_llm(text)

    def _on_hotkey_text(self, text: str) -> None:
        self.after(0, lambda: self._handle_hotkey_result(text))

    def _handle_hotkey_result(self, text: str) -> None:
        nb = self.master
        if isinstance(nb, ttk.Notebook):
            nb.select(self)
        self._orig.delete("1.0", "end")
        self._orig.insert("1.0", text)
        self._update_original_height()
        self._run_llm(text)
        top = self.winfo_toplevel()
        top.deiconify()
        top.lift()
        top.focus_force()

    # ------------------------------------------------------------------ LLM

    def _run_llm(self, text: str) -> None:
        if not self._config.api_key:
            messagebox.showwarning(
                "No API key",
                "Configure your API key in Settings first.",
                parent=self.winfo_toplevel(),
            )
            return

        self._clear_results()
        self._received = 0
        self._set_status(f"Polishing… (0/{len(TONES)})", "blue")
        config = self._config

        def on_result(r: PolishedText) -> None:
            self.after(0, lambda: self._add_result(text, r))

        def worker() -> None:
            try:
                polish_text(text, config, on_result=on_result)
                self.after(0, lambda: self._set_status(f"{len(TONES)} versions ready", "green"))
            except Exception as exc:
                error_msg = str(exc)
                logger.error(f"LLM error: {error_msg}")
                self.after(0, lambda msg=error_msg: self._show_llm_error(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _show_llm_error(self, error_msg: str) -> None:
        self._set_status("Error", "red")
        top = self.winfo_toplevel()

        dlg = tk.Toplevel(top)
        dlg.title("LLM Error")
        dlg.resizable(False, False)
        dlg.transient(top)
        dlg.grab_set()

        ttk.Label(dlg, text="An error occurred while calling the LLM:", font=("", 9)).pack(
            padx=16, pady=(14, 4), anchor="w"
        )
        txt = tk.Text(dlg, height=6, width=54, wrap="word", font=("", 9), state="normal")
        txt.insert("1.0", error_msg)
        txt.config(state="disabled")
        txt.pack(padx=16, pady=(0, 8))

        btn_row = ttk.Frame(dlg)
        btn_row.pack(pady=(0, 12))

        def open_log() -> None:
            dlg.destroy()
            try:
                os.startfile(str(LOG_PATH))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open log file:\n{e}", parent=top)

        ttk.Button(btn_row, text="Open Log", command=open_log).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Close", command=dlg.destroy).pack(side="left", padx=6)

        dlg.update_idletasks()
        x = top.winfo_rootx() + (top.winfo_width() - dlg.winfo_width()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")

    def _add_result(self, original: str, result: PolishedText) -> None:
        self._received += 1
        self._set_status(f"Polishing… ({self._received}/{len(TONES)})", "blue")
        item = _PolishedItem(
            self._results_frame,
            tone=result.tone,
            text=result.text,
            on_use=lambda tone, txt, orig=original: self._use_text(orig, tone, txt),  # type: ignore
        )

        insert_index = 0
        for existing in self._items:
            if TONES.index(existing._tone) > TONES.index(result.tone):
                break
            insert_index += 1

        if insert_index < len(self._items):
            item.pack(fill="x", padx=2, pady=2, before=self._items[insert_index])
            self._items.insert(insert_index, item)
        else:
            item.pack(fill="x", padx=2, pady=2)
            self._items.append(item)

    # ------------------------------------------------------------------ Use

    def _use_text(self, original: str, tone: str, text: str) -> None:
        save_history(original, text, tone)
        hwnd = self._hotkey.last_hwnd
        if hwnd and restore_focus_and_paste(hwnd, original, text):
            self._set_status(f"Pasted ({tone})", "green")
        else:
            pyperclip.copy(text)
            self._set_status(f"Copied to clipboard ({tone})", "gray")

    def _clear_all(self) -> None:
        self._orig.delete("1.0", "end")
        self._update_original_height()
        self._clear_results()
        self._set_status("", "gray")

    def _clear_results(self) -> None:
        for w in self._results_frame.winfo_children():
            w.destroy()
        self._items.clear()

    def _set_status(self, msg: str, color: str = "gray") -> None:
        self._status_var.set(msg)
        self._status_lbl.config(foreground=color)

    def cleanup(self) -> None:
        self._hotkey.disable()

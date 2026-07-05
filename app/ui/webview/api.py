"""Python <-> JS bridge exposed to the pywebview window as `pywebview.api`.

All methods here are called from app/ui/webview/web/app.js via the pywebview
js_api proxy, adapting business logic (LLM calls, storage, i18n, hotkey capture)
to a request/response + push-update shape a webview frontend can consume.
"""

import json
import os
import sys
import threading
import webbrowser
from typing import Any, Optional

import webview
from loguru import logger

from app.config import (
    APP_NAME,
    GOALS,
    GOALS_PRESET_DEFAULT,
    GOALS_PRESET_MIN,
    HOTKEY,
    LOG_PATH,
    OUTPUT_LANGUAGES,
    TONES,
    TRANSLATE_HOTKEY,
    UI_LANGUAGES,
)
from app.core import single_instance, updater
from app.core.autorun import configure_autorun
from app.core.focus import restore_focus_and_paste
from app.core.hotkey import HotkeyManager
from app.core.llm import check_connection, polish_text, translate_text
from app.db.database import (
    clear_history,
    get_history_count,
    load_autorun,
    load_config,
    load_history,
    load_selected_goals,
    load_selected_tone,
    load_translate_language,
    load_ui_language,
    save_autorun,
    save_config,
    save_history,
    save_selected_goals,
    save_selected_tone,
    save_translate_language,
    save_ui_language,
)
from app.i18n import Msg, goal_description, goal_name, t, tone_name
from app.schemas.models import AppConfig, Goal, Tone

try:
    import pyperclip
except ImportError:  # pragma: no cover - Windows-only runtime dependency
    pyperclip = None  # type: ignore[assignment]


def _js(value: Any) -> str:
    """Safely embed a Python value as a JS expression argument."""
    return json.dumps(value)


class Api:
    def __init__(self, version: str) -> None:
        self._version = version
        self._window: Optional[webview.Window] = None
        self._config: AppConfig = load_config()
        self._polish_hotkey = HotkeyManager(
            self._on_polish_hotkey, tap_key="alt", description=HOTKEY
        )
        self._translate_hotkey = HotkeyManager(
            self._on_translate_hotkey,
            tap_key="control",
            description=TRANSLATE_HOTKEY,
            capture_via_clipboard=True,
        )

    def attach_window(self, window: webview.Window) -> None:
        self._window = window
        self._polish_hotkey.enable()
        self._translate_hotkey.enable()
        threading.Thread(target=self._poll_show_signal, daemon=True).start()
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def shutdown(self) -> None:
        self._polish_hotkey.disable()
        self._translate_hotkey.disable()

    def _eval(self, js: str) -> None:
        if self._window is None:
            return
        try:
            self._window.evaluate_js(js)
        except Exception as e:
            logger.debug(f"evaluate_js failed: {e}")

    # ------------------------------------------------------------------ hotkeys

    def _on_polish_hotkey(self, text: str) -> None:
        self._eval(f"window.onHotkeyCapture('polish', {_js(text)})")
        self._show_window()

    def _on_translate_hotkey(self, text: str) -> None:
        self._eval(f"window.onHotkeyCapture('translate', {_js(text)})")
        self._show_window()

    def _show_window(self) -> None:
        if self._window is None:
            return
        try:
            self._window.show()
            self._window.restore()
        except Exception as e:
            logger.debug(f"show_window failed: {e}")

    def _poll_show_signal(self) -> None:
        import time

        while True:
            time.sleep(0.5)
            if single_instance.consume_show_signal():
                self._show_window()

    # ------------------------------------------------------------------ bootstrap

    def get_bootstrap(self) -> dict:
        strings = {m.name: t(m) for m in Msg}
        return {
            "version": self._version,
            "appName": APP_NAME,
            "strings": strings,
            "tones": [{"value": tn.value, "label": tone_name(tn)} for tn in TONES],
            "goals": [
                {"value": g.value, "label": goal_name(g), "description": goal_description(g)}
                for g in GOALS
            ],
            "goalPresets": {
                "minimum": [g.value for g in GOALS_PRESET_MIN],
                "default": [g.value for g in GOALS_PRESET_DEFAULT],
                "all": [g.value for g in GOALS],
            },
            "outputLanguages": list(OUTPUT_LANGUAGES.keys()),
            "outputLanguageMap": OUTPUT_LANGUAGES,
            "uiLanguages": list(UI_LANGUAGES.keys()),
            "uiLanguageMap": UI_LANGUAGES,
            "config": self._config.model_dump(mode="json"),
            "selectedTone": load_selected_tone().value,
            "selectedGoals": [g.value for g in load_selected_goals()],
            "translateLanguage": load_translate_language(),
            "uiLanguageCode": load_ui_language(),
            "autorun": load_autorun(),
            "polishHotkey": HOTKEY,
            "translateHotkey": TRANSLATE_HOTKEY,
        }

    # ------------------------------------------------------------------ settings

    def save_settings(self, payload: dict) -> dict:
        try:
            label = (payload.get("outputLanguage") or "").strip()
            output_language = OUTPUT_LANGUAGES.get(label, label) or "English"
            config = AppConfig(
                base_url=(payload.get("baseUrl") or "").strip(),
                model=(payload.get("model") or "").strip(),
                api_key=(payload.get("apiKey") or "").strip(),
                output_language=output_language,
                context=(payload.get("context") or "").strip(),
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}

        if not config.api_key:
            return {"ok": False, "error": t(Msg.API_KEY_REQUIRED)}
        if not config.model:
            return {"ok": False, "error": t(Msg.MODEL_REQUIRED)}

        goal_values = payload.get("goals") or []
        goals = [g for g in GOALS if g.value in goal_values]
        if not goals:
            return {"ok": False, "error": t(Msg.SELECT_AT_LEAST_ONE_GOAL)}

        save_config(config)
        save_selected_goals(goals)
        save_translate_language((payload.get("translateLanguage") or "").strip())
        self._config = config

        autorun = bool(payload.get("autorun"))
        save_autorun(autorun)
        configure_autorun(autorun)

        prev_ui_lang = load_ui_language()
        ui_lang = UI_LANGUAGES.get(payload.get("uiLanguage", ""), "en")
        save_ui_language(ui_lang)

        logger.info("Settings saved and applied")
        return {"ok": True, "restartRequired": ui_lang != prev_ui_lang}

    def test_connection(self, payload: dict) -> dict:
        label = (payload.get("outputLanguage") or "").strip()
        output_language = OUTPUT_LANGUAGES.get(label, label) or "English"
        config = AppConfig(
            base_url=(payload.get("baseUrl") or "").strip(),
            model=(payload.get("model") or "").strip(),
            api_key=(payload.get("apiKey") or "").strip(),
            output_language=output_language,
        )
        ok, message = check_connection(config)
        return {"ok": ok, "message": message}

    def restart_app(self) -> None:
        # Deliberately does not call self._window.destroy(): that fires pywebview's
        # `closing` event, which main.py's handler intercepts and turns into a hide
        # (not a real close) whenever autorun is on - the window would never actually
        # close and os.execv would replace a process still holding a visible window.
        # os.execv terminates this process outright, taking the window with it.
        self.shutdown()
        single_instance.release_lock()
        os.execv(sys.executable, [sys.executable, *sys.argv])

    # ------------------------------------------------------------------ polish

    def set_selected_tone(self, tone_value: str) -> None:
        try:
            save_selected_tone(Tone(tone_value))
        except ValueError:
            logger.debug(f"Invalid tone from frontend: {tone_value!r}")

    def polish(self, text: str, tone_value: str) -> dict:
        if not text.strip():
            return {"ok": False, "error": "empty"}
        if not self._config.api_key:
            return {"ok": False, "error": "no_api_key"}

        try:
            tone = Tone(tone_value)
        except ValueError:
            tone = TONES[0]

        goals = load_selected_goals()
        config = self._config

        def on_result(result) -> None:
            self._eval(
                f"window.onPolishResult({_js(text)}, "
                f"{_js({'goal': result.goal.value, 'text': result.text, 'tone': tone.value})})"
            )

        def worker() -> None:
            try:
                polish_text(text, tone, config, goals=goals, on_result=on_result)
                self._eval(f"window.onPolishDone({_js(text)})")
            except Exception as exc:
                logger.error(f"LLM error: {exc}")
                self._eval(f"window.onPolishError({_js(text)}, {_js(str(exc))})")

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def use_polished(self, original: str, tone_value: str, goal_value: str, text: str) -> dict:
        try:
            tone = Tone(tone_value)
            goal = Goal(goal_value)
        except ValueError:
            return {"ok": False}
        save_history(original, text, tone, goal)
        control = self._polish_hotkey.last_control
        hwnd = self._polish_hotkey.last_hwnd
        pasted = restore_focus_and_paste(control, hwnd, original, text)
        if not pasted and pyperclip is not None:
            pyperclip.copy(text)
        return {"ok": True, "pasted": pasted}

    def copy_text(self, text: str) -> dict:
        if pyperclip is not None:
            pyperclip.copy(text)
        return {"ok": True}

    # ------------------------------------------------------------------ translate

    def translate(self, text: str) -> dict:
        if not text.strip():
            return {"ok": False, "error": "empty"}
        config = load_config()
        if not config.api_key:
            return {"ok": False, "error": "no_api_key"}

        lang_label = load_translate_language()
        lang = OUTPUT_LANGUAGES.get(lang_label, lang_label)

        def worker() -> None:
            try:
                result = translate_text(text, lang, config)
                self._eval(f"window.onTranslateDone({_js(result)})")
            except Exception as exc:
                logger.error(f"Translation error: {exc}")
                self._eval(f"window.onTranslateError({_js(str(exc))})")

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    # ------------------------------------------------------------------ history

    def get_history(self, page: int, page_size: int) -> dict:
        offset = max(0, page) * page_size
        entries = load_history(limit=page_size, offset=offset)
        return {
            "entries": [
                {
                    "id": e.id,
                    "originalText": e.original_text,
                    "polishedText": e.polished_text,
                    "tone": tone_name(Tone(e.tone))
                    if e.tone in Tone._value2member_map_
                    else e.tone,
                    "goal": goal_name(Goal(e.goal))
                    if e.goal in Goal._value2member_map_
                    else e.goal,
                    "usedAt": e.used_at.strftime("%Y-%m-%d %H:%M"),
                }
                for e in entries
            ],
            "totalCount": get_history_count(),
        }

    def clear_history_action(self) -> dict:
        clear_history()
        return {"ok": True}

    # ------------------------------------------------------------------ updater

    def _check_update_worker(self) -> None:
        result = updater.check_for_update(self._version)
        if result:
            new_version, url = result
            self._eval(f"window.onUpdateAvailable({_js(new_version)}, {_js(url)})")

    def open_url(self, url: str) -> None:
        webbrowser.open(url)

    def open_log(self) -> dict:
        try:
            os.startfile(str(LOG_PATH))  # type: ignore[attr-defined]
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------ window / tray

    def close_window(self) -> None:
        if self._window is not None:
            self._window.destroy()

    def hide_to_tray(self) -> None:
        if self._window is not None:
            self._window.hide()

    def quit_app(self) -> None:
        self.shutdown()
        if self._window is not None:
            self._window.destroy()

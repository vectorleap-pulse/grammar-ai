"""Python <-> JS bridge exposed to the pywebview window as `pywebview.api`.

All methods here are called from app/ui/webview/web/app.js via the pywebview
js_api proxy, adapting business logic (LLM calls, storage, i18n, hotkey capture)
to a request/response + push-update shape a webview frontend can consume.
"""

import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
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
    UPDATE_CHECK_INTERVAL_MS,
)
from app.core import single_instance, updater
from app.core.autorun import configure_autorun
from app.core.focus import bring_to_foreground, restore_focus_and_paste
from app.core.hotkey import MOD_ALT, MOD_CONTROL, HotkeyManager
from app.core.llm import check_connection, polish_text, translate_text
from app.db.database import (
    clear_history,
    get_history_count,
    load_autorun,
    load_config,
    load_history,
    load_selected_goals,
    load_selected_tone,
    load_theme,
    load_translate_language,
    load_ui_language,
    save_autorun,
    save_config,
    save_history,
    save_selected_goals,
    save_selected_tone,
    save_theme,
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
        self._tray_icon: Any = None
        self._config: AppConfig = load_config()
        self._downloaded_installer_path: Optional[Path] = None
        self._notified_update_version: Optional[str] = None
        self._update_check_stop = threading.Event()
        self._update_check_thread: Optional[threading.Thread] = None
        self._restarting = False
        self._polish_hotkey = HotkeyManager(
            self._on_polish_hotkey,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk=ord("S"),
            description=HOTKEY,
        )
        self._translate_hotkey = HotkeyManager(
            self._on_translate_hotkey,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk=ord("D"),
            description=TRANSLATE_HOTKEY,
        )

    def attach_window(self, window: webview.Window) -> None:
        self._window = window
        self._polish_hotkey.enable()
        self._translate_hotkey.enable()
        threading.Thread(target=self._poll_show_signal, daemon=True).start()

        if self._update_check_thread is not None and self._update_check_thread.is_alive():
            self._update_check_stop.set()

        self._update_check_stop = threading.Event()
        self._update_check_thread = threading.Thread(
            target=self._run_update_check_loop, daemon=True
        )
        self._update_check_thread.start()

    def shutdown(self) -> None:
        self._polish_hotkey.disable()
        self._translate_hotkey.disable()
        self._update_check_stop.set()

    @property
    def is_restarting(self) -> bool:
        return self._restarting

    def attach_tray_icon(self, icon: Any) -> None:
        self._tray_icon = icon

    def stop_tray_icon(self) -> None:
        if self._tray_icon is None:
            return
        try:
            self._tray_icon.stop()
        except Exception as exc:
            logger.debug(f"tray icon stop failed: {exc}")
        finally:
            self._tray_icon = None

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
            # window.show()/restore() alone only un-hide/un-minimize - they don't
            # reliably grab OS foreground focus when called off the hotkey hook's
            # worker thread (see bring_to_foreground's docstring for why).
            bring_to_foreground(self._window.native.Handle.ToInt64())  # type: ignore[attr-defined]
        except Exception as e:
            logger.debug(f"show_window failed: {e}")

    def _poll_show_signal(self) -> None:
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
            "theme": load_theme(),
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

    def save_theme_setting(self, theme: str) -> dict:
        try:
            save_theme(theme)
            return {"ok": True}
        except Exception as exc:
            logger.exception("theme save failed")
            return {"ok": False, "error": str(exc)}

    def restart_app(self) -> None:
        # Spawns the replacement process explicitly via subprocess.Popen rather than
        # os.execv: on Windows, os.execv is emulated by the CRT via spawn-and-wait
        # rather than true in-place process replacement (unlike on Unix), and that
        # emulation has been observed to silently fail to hand off to a new process
        # at all when the parent's console is a Git Bash/MSYS shell (a common
        # terminal on Windows dev machines) - the old process just exits and nothing
        # new ever starts, with no error anywhere. subprocess.Popen sidesteps that
        # fragility entirely.
        #
        # Popen happens BEFORE window.destroy(), not after: destroying the window
        # unblocks pywebview's blocking webview.start() call on the *main* thread,
        # letting main() reach its end and the whole process start shutting down
        # naturally - and this method itself normally runs on a background thread
        # (pywebview's JS-bridge dispatch), which Python kills mid-execution the
        # instant the main thread exits, without waiting for it. Spawning the
        # replacement first means it exists as an independent process before
        # anything here can race to end this one - confirmed via a live repro that
        # this ordering matters: with a tray-icon thread also present (as the real
        # app always has), destroy-then-Popen consistently lost that race and the
        # replacement was never created, even though it looked fine without a tray
        # icon. The new process's own webview init still won't happen until after
        # its own Python/import/DB startup, by which point the old window (destroyed
        # right after Popen returns, below) is long gone - so this doesn't reintroduce
        # the WebView2 user-data-folder lock contention that not destroying the
        # window at all originally caused.
        logger.info("restart_app: starting restart sequence")
        self._restarting = True
        self.shutdown()
        self.stop_tray_icon()
        single_instance.release_lock()
        # CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS: Git Bash/MSYS (a common
        # terminal on Windows dev machines) runs launched processes inside a Windows
        # Job Object and a shared console - a plain child inherits both, so it gets
        # silently killed when this parent process exits below (or when the parent
        # shell's console/pty tears down), even though the child is otherwise a fully
        # independent process. Breaking away from the job and detaching from the
        # console (this is a GUI app - it doesn't need one) is what makes it survive.
        # `sys.executable` (python.exe, for a from-source run) is a console-subsystem
        # binary, though - DETACHED_PROCESS only stops it inheriting *our* console, it
        # doesn't stop the CRT from auto-allocating a fresh one the moment anything
        # tries to write to stdout/stderr with no console attached (e.g. main.py's own
        # `logger.add(sys.stderr, ...)`), which is what caused an empty console window
        # to flash up. Redirecting all three standard streams to DEVNULL means that
        # write has somewhere to go that isn't "summon a console."
        try:
            proc = subprocess.Popen(
                [sys.executable, *sys.argv],
                creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB  # type: ignore[attr-defined]
                | subprocess.DETACHED_PROCESS,  # type: ignore[attr-defined]
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"restart_app: replacement process spawned, pid={proc.pid}")
        except Exception:
            # Logged (not just debug) since this is the one failure mode that would
            # otherwise vanish silently: this runs on pywebview's JS-bridge dispatch,
            # entirely outside main.py's own startup try/except that writes
            # ERROR_LOG_PATH, so an uncaught exception here would never reach either
            # log - pywebview's own bridge dispatcher would catch and swallow it.
            logger.exception("restart_app: failed to spawn replacement process")
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception as exc:
                logger.debug(f"window.destroy failed during restart: {exc}")
        logger.info("restart_app: window destroyed, exiting old process now")
        # Best-effort grace period for the old WebView2 host subprocess to actually
        # release its user-data-folder lock before os._exit (harmless now that Popen
        # already ran, but still avoids leaving the OS a fully torn-down window vs.
        # a still-finishing one to sort out at the same instant as process exit).
        time.sleep(0.3)
        os._exit(0)

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
        hwnd = self._polish_hotkey.last_hwnd
        pasted = restore_focus_and_paste(hwnd, original, text)
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

    def _run_update_check_loop(self) -> None:
        while not self._update_check_stop.is_set():
            self._check_update_worker()
            self._update_check_stop.wait(UPDATE_CHECK_INTERVAL_MS / 1000.0)

    def _check_update_worker(self) -> None:
        info = updater.check_for_update(self._version)
        if info is None:
            return
        if self._notified_update_version == info.version:
            return
        try:
            downloads_dir = updater.get_downloads_folder()
            path = updater.download_installer(info.download_url, downloads_dir)
        except Exception as e:
            # Download failures aren't surfaced to the UI - just retried on the next
            # check, same as check_for_update() already does for its own failures.
            logger.warning(f"Update download failed: {e}")
            return
        self._downloaded_installer_path = path
        self._notified_update_version = info.version
        self._eval(f"window.onUpdateAvailable({_js(info.version)})")

    def open_installer_and_quit(self) -> dict:
        if self._downloaded_installer_path is None:
            return {"ok": False}
        updater.open_containing_folder(self._downloaded_installer_path)
        # Deliberately not self.quit_app(): it also force-exits via os._exit() below,
        # but only after a best-effort self._window.destroy() first (which fires
        # pywebview's `closing` event, intercepted into a window.hide() by main.py's
        # handler when autorun is on, before the os._exit() cuts in anyway). Skipping
        # destroy() here avoids that pointless destroy()/hide() detour, since Explorer
        # is about to take focus regardless. os._exit() (not sys.exit()) is used since
        # a background thread calling sys.exit() would only terminate that thread, not
        # the process.
        self.shutdown()
        self.stop_tray_icon()
        single_instance.release_lock()
        os._exit(0)

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
        self.stop_tray_icon()
        single_instance.release_lock()
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception as exc:
                logger.debug(f"window.destroy failed during quit: {exc}")
        os._exit(0)

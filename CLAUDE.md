# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependency management is via `uv` (not pip/poetry directly).

```bash
uv sync --extra dev          # install runtime + dev deps (ruff, mypy, pyinstaller, tomli_w)
uv run python main.py        # run the app from source
uv run python main.py --tray-only   # run minimized to the system tray

uv run python lint.py        # ruff format + ruff check --fix + mypy (what CI runs)
uv run ruff format .
uv run ruff check --fix .
uv run mypy .

uv run python build.py       # PyInstaller onedir build -> build/grammar-ai/
uv run python build.py --debug   # same, but console-attached for debugging
```

There is no test suite in this repository.

CI (`.github/workflows/lint.yml`) runs `lint.py` on every PR to `main`, on `ubuntu-latest`, even
though the app itself is Windows-only at runtime. `.github/workflows/build-release.yml` is a
manual (`workflow_dispatch`) job on `windows-latest` that bumps the version, builds via
`build.py`, packages with Inno Setup (`installer.iss`), and publishes a GitHub Release.

## Architecture

Grammar AI is a **Windows-only** Python 3.12 + Tkinter desktop utility (not a browser extension,
despite the `grammar-ai-ext` directory name). Its core interaction model: press a global hotkey
anywhere in Windows, capture the focused text field's content, send it to an LLM, and paste the
result back into the same field.

**Entry point**: `main.py` acquires a single-instance lock, initializes the SQLite DB, sets the UI
language, configures autorun, then constructs `app.ui.main_window.MainWindow` (a `tk.Tk` subclass)
and runs the Tkinter mainloop.

**`app/core/` — OS integration, all Windows-specific (`ctypes` calls into `user32.dll`/`kernel32.dll`)**:
- `hotkey.py` — registers global hotkeys via raw Win32 `RegisterHotKey` and captures the focused
  control's text via **UI Automation** (`uiautomation` package: `ValuePattern`/`TextPattern`), not
  the clipboard. `HotkeyManager` runs its own Win32 message loop on a dedicated thread per
  registered hotkey; `PolishTab` and `TranslateTab` each own one, differing only in modifier/VK
  and callback. There are two Chromium/Electron-hosted-app quirks handled here: a retry after
  `_COLD_START_RETRY_DELAY_SECONDS` because Chromium only activates its full accessibility tree
  once it detects an AT client querying it, so the very first read can come back empty.
- `focus.py` — writes the polished/translated text back into the originally focused control via
  UI Automation (`ValuePattern.SetValue`), keyed off the `Control` reference (`last_control`)
  captured by `HotkeyManager`, not by re-focusing and simulating keystrokes.
- `single_instance.py` — named Win32 mutex + event so a second launch focuses the existing window
  instead of starting a new process.
- `autorun.py` — writes/removes a value under `HKCU\...\Run` for start-on-login.
- `updater.py` — polls the GitHub Releases API for `vectorleap-pulse/grammar-ai` and surfaces a
  dismissible update banner in `MainWindow`.
- `llm.py` — the only non-Windows-specific module here: an OpenAI-compatible client (BYO base
  URL/key/model — Groq, OpenAI, etc., configured in Settings) used for both Polish and Translate.

**Important**: nothing in `app/core/hotkey.py` or `app/core/focus.py` touches the system clipboard
or simulates keystrokes. That's a deliberate constraint, not an oversight — the previous
clipboard-blank/simulate-Ctrl+C/poll/restore approach was flagged by some AV/EDR products
(Bitdefender confirmed) as malware-like behavior. Do not reintroduce `pyperclip`/`pyautogui`-based
capture or paste-back. `pyperclip` is still used elsewhere for explicit, user-clicked "Copy"
buttons (`polish_tab.py`, `translate_tab.py`) — that one-shot, user-initiated pattern is fine and
distinct from the programmatic capture loop that was removed.

**`app/ui/`** — Tkinter widgets. `main_window.py` hosts a `ttk.Notebook` with three tabs
(`app/ui/tabs/polish_tab.py`, `translate_tab.py`, `history_tab.py`) plus the tray icon (`pystray`)
and the update banner. Each tab constructs its own `HotkeyManager` and wires the callback back
into the tab via `.after(0, ...)` for Tkinter thread safety, since hotkey capture happens on a
background thread.

**`app/db/database.py`** — SQLite at `~/.grammar-ai/data.db` (see `app/config.py` for paths).
Stores settings (including the API key, in plaintext) and Polish history (capped at
`HISTORY_MAX_ENTRIES`, currently 1000); Translate results are not persisted.

**`app/i18n.py`** — UI string table for en/es/fr/de/ja/ko, independent of the Polish output
language and Translate target language (both separately configurable in Settings, see
`OUTPUT_LANGUAGES` in `app/config.py`).

**`app/config.py`** — the single place for constants: hotkey key combos, tone/goal lists, output
language maps, DB paths, the update-check URL/interval, window geometry, and the frozen-build
resource-path logic (handles both PyInstaller's `sys._MEIPASS` and Nuitka's `__compiled__`).

## Conventions

- Do not use em-dashes in code, commit messages, or documentation in this repository.
- Prefer Context7 (MCP) for looking up current library/API documentation rather than relying on
  training-data knowledge, particularly for the Windows-specific packages (`uiautomation`,
  `pystray`) and `openai` SDK usage.
- Commit messages in this repository follow a terse, no-fluff "caveman commit" style: short,
  direct, imperative, no filler words or hedging (e.g. `fix hotkey capture`, `add translate tab`,
  not `This commit fixes an issue where...`).

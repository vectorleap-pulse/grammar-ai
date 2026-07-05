# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependency management is via `uv` (not pip/poetry directly) for the Python app, and `pnpm` for
the frontend.

```bash
uv sync --extra dev          # install runtime + dev deps (ruff, mypy, pyinstaller, tomli_w)

cd frontend && pnpm install && pnpm build   # build the React UI -> app/ui/webview/web/
                                             # (generated/gitignored - required before
                                             # `main.py` will have a UI to load, and after
                                             # every change under frontend/src/)

uv run python main.py        # run the app from source
uv run python main.py --tray-only   # run minimized to the system tray

uv run python lint.py        # ruff format + ruff check --fix + mypy (what CI runs)
uv run ruff format .
uv run ruff check --fix .
uv run mypy .

uv run python build.py       # builds the frontend, then PyInstaller onedir build -> build/grammar-ai/
uv run python build.py --debug   # same, but console-attached for debugging
```

There is no test suite in this repository (Python or frontend).

CI (`.github/workflows/lint.yml`) runs `lint.py` on every PR to `main`, on `ubuntu-latest`, even
though the app itself is Windows-only at runtime - it only lints Python, so it doesn't need Node.
`.github/workflows/build-release.yml` is a manual (`workflow_dispatch`) job on `windows-latest`
that bumps the version, sets up pnpm/Node, builds via `build.py` (which builds the frontend
first), packages with Inno Setup (`installer.iss`), and publishes a GitHub Release.

## Architecture

Grammar AI is a **Windows-only** Python 3.12 desktop utility (not a browser extension, despite the
`grammar-ai-ext` directory name). Its core interaction model: press a global hotkey anywhere in
Windows, capture the focused text field's content, send it to an LLM, and paste the result back
into the same field.

**Entry point**: `main.py` acquires a single-instance lock, initializes the SQLite DB, sets the UI
language, configures autorun, then launches the UI (`pywebview`, a React frontend in an embedded
WebView2 window - the only UI; there is no other launch mode besides `--tray-only`).

**`frontend/`** — the UI's source: a React + TypeScript SPA built with Vite, styled with
Tailwind v4 and shadcn components (retheme-matched to the app's original vanilla-JS look, not
shadcn's defaults - see `frontend/src/index.css`'s `@theme`/`:root` blocks). `frontend/vite.config.ts`
builds directly into `app/ui/webview/web/` (`base: "./"`, since the page loads over `file://`
inside WebView2, not a web server root - a `crossorigin` on the emitted `<script>`/`<link>` tags
would otherwise fail WebView2's CORS check for that null origin, so a small Vite plugin strips it).
`app/ui/webview/web/` itself is **generated output, gitignored** - run `pnpm build` inside
`frontend/` after any change under `frontend/src/` (see Commands above).

**`app/ui/webview/`** — `api.py`'s `Api` class, exposed as `pywebview.api` in the frontend
(typed in `frontend/src/lib/pywebview.ts`). `Api` adapts business logic (LLM calls, storage,
i18n) to a request/response + push-update shape: long-running calls like `polish()`/`translate()`
spawn a background thread and push partial results into the page via `window.evaluate_js(...)`,
calling `window.onPolishResult(...)`/`onTranslateDone(...)`/etc. globals - these are plain
`window` globals assigned by React effects (`App.tsx`, `hooks/usePolish.ts`,
`hooks/useTranslate.ts`), not React state/props, since Python has no way to call into React
directly. `Api` also owns the two `HotkeyManager` instances (Polish and Translate) directly -
hotkey capture pushes into the page via `window.onHotkeyCapture(kind, text)`. i18n strings are
not duplicated in the frontend: `Api.get_bootstrap()` serializes the full current-language string
table (all `Msg` members) once at load, and components render from that dict via
`hooks/useBootstrap.tsx`'s context.

**`app/core/` — OS integration, all Windows-specific (`ctypes` calls into `user32.dll`/`kernel32.dll`)**:
- `hotkey.py` — global hotkeys are double-taps of a lone modifier (Polish: double-tap Shift,
  Translate: double-tap Ctrl), not `RegisterHotKey` combos - `RegisterHotKey` can't represent
  "a modifier pressed twice alone", so `HotkeyManager` installs its own `WH_KEYBOARD_LL` low-level
  keyboard hook per instance and times taps itself, tracking every currently-held key so a tap
  used as part of any chord is never mistaken for a solo double-tap. `Api` owns one instance each
  for Polish and Translate, each on its own dedicated thread (hooks need a live `GetMessageW` loop
  on the installing thread). Polish's capture reads the focused control's text via **UI Automation**
  (`uiautomation` package: `ValuePattern`/`TextPattern`), not the clipboard - a Chromium/Electron
  cold-start quirk is handled here (a retry after `_COLD_START_RETRY_DELAY_SECONDS`, since Chromium
  only activates its full accessibility tree once it detects an AT client querying it, so the very
  first read can come back empty). Translate's capture is a deliberate exception
  (`capture_via_clipboard=True`): clipboard-blank + simulated Ctrl+C + poll + restore, see below.
- `focus.py` — writes the polished/translated text back into the originally focused control via
  UI Automation (`ValuePattern.SetValue`), keyed off the `Control` reference (`last_control`)
  captured by `HotkeyManager`, not by re-focusing and simulating keystrokes.
- `single_instance.py` — named Win32 mutex + event so a second launch focuses the existing window
  instead of starting a new process.
- `autorun.py` — writes/removes a value under `HKCU\...\Run` for start-on-login.
- `updater.py` — polls the GitHub Releases API for `vectorleap-pulse/grammar-ai`; `Api` surfaces a
  dismissible update banner via `window.onUpdateAvailable(...)`.
- `llm.py` — the only non-Windows-specific module here: an OpenAI-compatible client (BYO base
  URL/key/model — Groq, OpenAI, etc., configured in Settings) used for both Polish and Translate.

**Important**: `app/core/focus.py` and Polish's capture path in `app/core/hotkey.py` don't touch
the system clipboard or simulate keystrokes - a deliberate constraint, not an oversight. The
clipboard-blank/simulate-Ctrl+C/poll/restore approach was flagged by some AV/EDR products
(Bitdefender confirmed) as malware-like behavior, which is why Polish and all paste-back avoid it.
**Translate's capture is a scoped, deliberate exception** (`HotkeyManager(..., capture_via_clipboard=True)`
in `api.py`): it does use that clipboard/`pyautogui` pattern, trading the same AV-heuristic risk
for broader compatibility with apps that don't expose text via accessibility APIs. Don't "fix"
this back to UI Automation without checking with whoever owns this decision first, and don't
spread clipboard/keystroke-sim to Polish or to any paste-back path - this exception is Translate's
capture only. `pyperclip` is also used, separately, for explicit user-clicked "Copy" buttons
(`Api.copy_text()`, wired to the Copy buttons in `ResultCard.tsx`/`TranslateTab.tsx`) - a one-shot,
user-initiated pattern distinct from both of the above.

**`app/db/database.py`** — SQLite at `~/.grammar-ai/data.db` (see `app/config.py` for paths).
Stores settings (including the API key, in plaintext) and Polish history (capped at
`HISTORY_MAX_ENTRIES`, currently 1000); Translate results are not persisted.

**`app/i18n.py`** — UI string table for en/es/fr/de/ja/ko, independent of the Polish output
language and Translate target language (both separately configurable in Settings, see
`OUTPUT_LANGUAGES` in `app/config.py`).

**`app/config.py`** — the single place for constants: hotkey display strings, tone/goal lists, output
language maps, DB paths, the update-check URL/interval, window geometry, and the frozen-build
resource-path logic (handles both PyInstaller's `sys._MEIPASS` and Nuitka's `__compiled__`).

## Conventions

- Do not use em-dashes in code, commit messages, or documentation in this repository.
- Prefer Context7 (MCP) for looking up current library/API documentation rather than relying on
  training-data knowledge, particularly for the Windows-specific packages (`uiautomation`,
  `pystray`), `openai` SDK usage, and the frontend stack (Vite, Tailwind v4, shadcn/Base UI).
- Commit messages in this repository follow a terse, no-fluff "caveman commit" style: short,
  direct, imperative, no filler words or hedging (e.g. `fix hotkey capture`, `add translate tab`,
  not `This commit fixes an issue where...`).

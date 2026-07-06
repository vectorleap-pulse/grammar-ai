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

uv run python lint.py        # ruff format + ruff check --fix + mypy + frontend prettier/oxlint
uv run ruff format .
uv run ruff check --fix .
uv run mypy .

cd frontend && pnpm run format   # prettier --write . (what lint.py runs)
cd frontend && pnpm run lint     # oxlint (what lint.py runs, with --fix)

uv run python build.py       # builds the frontend, then PyInstaller onedir build -> build/grammar-ai/
uv run python build.py --debug   # same, but console-attached for debugging
```

There is no test suite in this repository (Python or frontend).

CI (`.github/workflows/lint.yml`) runs `lint.py` on every PR to `main`, on `ubuntu-latest`. Even
though the app itself is Windows-only at runtime, `lint.py` also runs the frontend's prettier +
oxlint (see `frontend/package.json`), so this workflow sets up pnpm/Node too, same as
`build-release.yml` below. `.github/workflows/build-release.yml` is a manual (`workflow_dispatch`)
job on `windows-latest` that bumps the version, sets up pnpm/Node, builds via `build.py` (which
builds the frontend first), packages with Inno Setup (`installer.iss`), and publishes a GitHub
Release.

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
shadcn's defaults - see `frontend/src/index.css`'s `@theme`/`:root` blocks; Input/Textarea's
focus and invalid states were also simplified from shadcn's defaults, dropping the colored
`ring-*` glow in favor of a plain `border-foreground/70` on focus, to avoid a distracting mix of
border colors across the many stacked text fields in Settings and the result cards).
`frontend/vite.config.ts` builds directly into `app/ui/webview/web/` (`base: "./"`, since the page
loads over `file://` inside WebView2, not a web server root - a `crossorigin` on the emitted
`<script>`/`<link>` tags would otherwise fail WebView2's CORS check for that null origin, so a
small Vite plugin strips it). `app/ui/webview/web/` itself is **generated output, gitignored** -
run `pnpm build` inside `frontend/` after any change under `frontend/src/` (see Commands above).

`Titlebar.tsx` hosts the Settings, theme-toggle, and Close buttons directly (moved out of the nav
bar) plus the app version string, and is the `pywebview-drag-region` for frameless-window
dragging. `ui/dialog.tsx`/`ui/alert-dialog.tsx`'s overlays are offset `top-10` rather than
`inset-0` so the titlebar stays visible/draggable while a dialog is open. `App.tsx` binds Escape
to `close_window()` globally, except while focus is in an input/textarea/select or a dialog/error
alert is open (so it doesn't swallow the key from inside those).

**`app/ui/webview/`** — `api.py`'s `Api` class, exposed as `pywebview.api` in the frontend
(typed in `frontend/src/lib/pywebview.ts`). `Api` adapts business logic (LLM calls, storage,
i18n) to a request/response + push-update shape: long-running calls like `polish()`/`translate()`
spawn a background thread and push partial results into the page via `window.evaluate_js(...)`,
calling `window.onPolishResult(...)`/`onTranslateDone(...)`/etc. globals - these are plain
`window` globals assigned by React effects (`App.tsx`, `hooks/usePolish.ts`,
`hooks/useTranslate.ts`), not React state/props, since Python has no way to call into React
directly. `Api` also owns the two `HotkeyManager` instances (Polish and Translate) directly -
hotkey capture pushes into the page via `window.onHotkeyCapture(kind, text)` - and holds a
reference to the system tray icon (`attach_tray_icon()`, called from `main.py`'s `_run_tray()`),
so `quit_app()`/`open_installer_and_quit()` can stop pystray's icon loop (`stop_tray_icon()`) as
part of their hard-exit sequence, not just tear down the window. i18n strings are
not duplicated in the frontend: `Api.get_bootstrap()` serializes the full current-language string
table (all `Msg` members) once at load, and components render from that dict via
`hooks/useBootstrap.tsx`'s context.

**`app/core/` — OS integration, all Windows-specific (`ctypes` calls into `user32.dll`/`kernel32.dll`)**:
- `hotkey.py` — global hotkeys are real key combos (Polish: Ctrl+Alt+A, Translate: Ctrl+Alt+D)
  registered via Win32 `RegisterHotKey`, delivered as `WM_HOTKEY` on the registering thread's
  message queue. `Api` owns one `HotkeyManager` instance each for Polish and Translate, each on
  its own dedicated thread (`RegisterHotKey(hWnd=None, ...)` ties the registration to the calling
  thread, which must keep pumping `GetMessageW` for as long as the hotkey should fire).
  Both hotkeys capture the focused control's text the same way: clipboard-blank + simulated
  Ctrl+C + poll + restore (falling back to Ctrl+A, Ctrl+C if nothing was selected). `last_hwnd`
  (the foreground window at hotkey time) is the only thing remembered afterward - paste-back
  (`focus.py`) works off that window handle alone, not a captured control reference.
- `clipboard.py` — `poll_clipboard(timeout)`, the polling loop shared by `hotkey.py`'s capture and
  `focus.py`'s paste-back (poll `pyperclip.paste()` every 25ms until non-empty or timeout).
- `focus.py` — writes the polished text back into the originally focused window via the same
  clipboard-blank/simulate-keys/poll/restore family as capture, applied to writing: refocus the
  window (`bring_to_foreground`), select-all + copy to read its *current* live content, replace
  the captured `original` substring with the polished text against that live read (not a stale
  value), write the merged result to the clipboard, then select-all + paste - restoring the user's
  prior clipboard contents afterward. Bails out (returns `False`, letting `Api.use_polished()` fall
  back to a plain clipboard copy) if the original window can't be brought back to the actual OS
  foreground, rather than risking sending Select-All/Paste into whatever window - possibly Grammar
  AI's own - happens to be focused instead.
- `single_instance.py` — named Win32 mutex + event so a second launch focuses the existing window
  instead of starting a new process.
- `autorun.py` — writes/removes a value under `HKCU\...\Run` for start-on-login.
- `updater.py` — polls the GitHub Releases API for `vectorleap-pulse/grammar-ai`; on finding a
  newer release, downloads its installer to the user's real Downloads folder (resolved via
  `SHGetKnownFolderPath`/`FOLDERID_Downloads`, not `Path.home() / "Downloads"` - the user may have
  relocated it or have OneDrive Known Folder Move redirecting it elsewhere), atomically (temp file
  + `os.replace`, so a crash mid-download never leaves a truncated file at the path the
  already-downloaded check looks for) and idempotently (skips re-downloading if that
  version-qualified filename already exists), then marks it with the Mark-of-the-Web
  zone-identifier so SmartScreen treats it exactly as it would a manual browser download. `Api`
  surfaces a dismissible banner via `window.onUpdateAvailable(version)` once the download
  succeeds. **The app never executes the downloaded installer itself** -
  `Api.open_installer_and_quit()` only opens Explorer with it selected
  (`updater.open_containing_folder`) and then hard-exits; the installer only ever runs from an
  explicit user double-click. This is deliberate: a process that downloads and executes an
  unsigned binary itself is a common dropper-behavior signature that AV/EDR heuristics watch for -
  this codebase has already been burned once by a different flagged pattern (see the
  clipboard-capture note below), so the update flow is designed to never create that one.
  `open_installer_and_quit()` skips `Api.quit_app()` (see its own comment) - not because
  `quit_app()` fails to exit (it also force-exits via `os._exit()` after a best-effort
  `window.destroy()`), but because Explorer is about to take focus regardless, so there's no need
  for the destroy()/closing-event dance first. Both methods share the same `shutdown()` +
  `stop_tray_icon()` + `release_lock()` + `os._exit(0)` hard-exit tail, but `restart_app()` inserts
  a `subprocess.Popen([sys.executable, *sys.argv])` **before** `window.destroy()`, not after - not
  `os.execv`, which on Windows is CRT-emulated via spawn-and-wait rather than true in-place
  replacement, and has been observed to silently fail to hand off at all under a Git Bash/MSYS
  parent shell. `Popen` must run before `destroy()` specifically: `restart_app()` normally runs on
  a background thread (pywebview's JS-bridge dispatch), and `window.destroy()` unblocks
  `webview.start()`'s blocking call on the *main* thread, letting `main()` finish and the process
  start shutting down naturally - which kills that background thread (a daemon thread) mid-flight
  before it reaches `Popen`, if `Popen` hasn't already run by then. Confirmed via a live repro: this
  race is timing-dependent (invisible in a minimal repro, but reliably fatal once a tray-icon
  thread - which the real app always has - is also shutting down concurrently), so spawn-then-destroy
  isn't a stylistic preference, it's what makes the replacement process reliably exist at all.
  The `Popen` call also needs `creationflags=CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS`: Git
  Bash/MSYS runs launched processes inside a Windows Job Object and a shared console, and a plain
  child inherits both, getting silently killed the moment this process exits (or its parent shell's
  console/pty tears down) without either flag - also confirmed via a live repro (spawn, check
  `tasklist`, not just absence of an exception), since relying on inherited stdout to observe a
  `DETACHED_PROCESS` child is itself unreliable.
- `llm.py` — the only non-Windows-specific module here: an OpenAI-compatible client (BYO base
  URL/key/model — Groq, OpenAI, etc., configured in Settings) used for both Polish and Translate.

**Important**: both hotkeys' capture (`app/core/hotkey.py`) and Polish's paste-back (`app/core/focus.py`)
use the clipboard-blank/simulate-keys/poll/restore pattern, trading the same AV-heuristic risk
(this pattern is structurally identical to how clipboard-hijacking malware behaves and has
previously been flagged as such by some AV/EDR products - Bitdefender confirmed) for broader
compatibility with apps that don't expose text via accessibility APIs, or whose UI Automation
support doesn't behave like a real user edit. Both capture and paste-back were originally
Translate-only (Translate has no paste-back, so this only ever meant capture for Translate);
Polish was deliberately kept on UI-Automation-only capture and paste-back to avoid that AV risk,
then later migrated onto the same clipboard pattern as Translate for both - two separate,
owner-approved reversals of that original decision, not oversights. As of this migration, nothing
in the codebase uses the `uiautomation` package any more, and it has been dropped from
`pyproject.toml`. `pyperclip` is also used, separately, for explicit user-clicked "Copy" buttons
(`Api.copy_text()`, wired to the Copy buttons in `ResultCard.tsx`/`TranslateTab.tsx`) - a one-shot,
user-initiated pattern distinct from the programmatic capture/paste-back loops above.

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
  training-data knowledge, particularly for the Windows-specific packages (`pyautogui`,
  `pyperclip`, `pystray`), `openai` SDK usage, and the frontend stack (Vite, Tailwind v4, shadcn/Base UI).
- Commit messages in this repository follow a terse, no-fluff "caveman commit" style: short,
  direct, imperative, no filler words or hedging (e.g. `fix hotkey capture`, `add translate tab`,
  not `This commit fixes an issue where...`).

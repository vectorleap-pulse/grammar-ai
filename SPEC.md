# Grammar AI - Specification

## Purpose

A free, lightweight Windows desktop utility that rewrites and translates text in place, in any
application, via a global hotkey. The user selects or focuses text anywhere in Windows, presses a
hotkey, and gets AI-generated results they can paste back without leaving the app they were in.

## Platform

Windows only. No browser extension, no Linux/macOS support at this time.

## Core features

### Polish

- Global hotkey (double-tap **Shift**) captures the focused control's text (selection if present,
  otherwise the full field) and sends it to the Polish tab.
- Rewrites the captured text into one or more **tones** (Professional, Casual, Chatting, Formal,
  Friendly, Empathetic, Assertive, Diplomatic), each generated for every configured **goal**
  (Inform, Persuade, Reassure, Motivate, Clarify, Apologize, Request, Acknowledge, Engage, Review,
  Clean) concurrently.
- Optional **cross-lingual polishing**: a configurable output language translates the source text
  before applying tone/goal rewriting.
- Each result has "Use" (paste back into the originating control) and "Copy" (explicit clipboard
  copy) actions. Shift+1 through Shift+9 and Shift+0 (app-level, only while the Polish tab has
  focus) trigger "Use" on the 1st through 10th result card, as a keyboard alternative to clicking.
- Every Polish result is saved to History (original text, polished text, tone, goal, timestamp).

### Translate

- Global hotkey (double-tap **Ctrl**) captures the focused control's text, into the Translate tab
  (see "Capture and paste-back mechanism" below - Translate's capture mechanism differs from
  Polish's).
- Direct translation into a configurable target language, independent of the Polish output
  language.
- "Copy" action only; Translate results are not saved to History.

### History

- Lists saved Polish results, most recent first, capped at 1000 entries (oldest dropped).

### Settings

- OpenAI-compatible API configuration: base URL, model, API key (any provider - Groq, OpenAI,
  etc.).
- Goal selection for Polish generation, optional free-text context to steer output.
- Polish output language and Translate target language (independently configurable).
- UI language (en/es/fr/de/ja/ko), independent of both output languages.
- Autorun-on-login toggle.

### System integration

- System tray icon (open/quit), with an optional `--tray-only` launch mode.
- Single-instance enforcement: a second launch focuses the existing window instead of starting a
  new process.
- Background auto-update check against GitHub Releases, surfaced as a dismissible in-app banner
  linking to the release page (no silent self-update).

## Capture and paste-back mechanism

**Polish** capture and paste-back are implemented via **Windows UI Automation**
(`ValuePattern`/`TextPattern` on the OS accessibility tree), not the clipboard and not simulated
keystrokes:

- The clipboard-blank/simulate-`Ctrl+C`/poll/restore approach is structurally identical to
  clipboard-hijacking malware behavior and was flagged as such by Bitdefender and likely other
  AV/EDR heuristics.
- UI Automation reads/writes the focused control's text directly via synchronous COM calls - no
  clipboard access, no synthetic keystroke injection, and (per informal measurement against the
  clipboard-based implementation's fixed `time.sleep` calls) roughly 350-650ms less latency per
  capture/paste-back cycle for supported apps.
- `pyperclip` remains in use elsewhere only for explicit, user-clicked "Copy" buttons - a
  one-shot, user-initiated clipboard write is a different, non-flagged pattern from a
  programmatic capture loop.

**Coverage is bounded by what the target app exposes to UI Automation**, not universal:

| Tier | Examples | Expected support |
|---|---|---|
| High confidence | Microsoft Word, Microsoft Teams, Notepad and other plain Win32 edit controls | Reliable |
| Likely compatible (compose box) | Discord, Slack, WhatsApp Desktop, Signal Desktop (desktop and web, in Chrome/Edge) | Reliable for the compose field specifically, after a short accessibility-tree "cold start" retry |
| Higher risk | Telegram Desktop (Qt, inconsistent custom-widget accessibility instrumentation) | Uncertain |
| Known gap | VS Code's Monaco code-editing surface (virtualized rendering, hidden-textarea input capture, selection state not exposed by default) | Likely unsupported; VS Code's non-editor UI (dialogs, search, sidebar) is unaffected |

When a focused control exposes neither `ValuePattern` nor `TextPattern`, Polish capture fails
explicitly rather than silently falling back to a clipboard-based mechanism. The safe manual
alternative for unsupported apps: the user copies text themselves via the OS and pastes it into
Grammar AI's own text field, since that never invokes a clipboard API from the app's own code.

**Translate** capture, by deliberate exception, uses the clipboard-blank/simulate-`Ctrl+C`/poll/
restore approach described above (selecting all text first if nothing is already selected),
restoring the user's prior clipboard contents afterward. This trades the same AV-heuristic risk
UI Automation was introduced to avoid for broader compatibility with apps that don't expose text
via accessibility APIs - an explicit, scoped choice for Translate only. Translate has no
paste-back (its output is Copy-button-only), so this only affects how Translate's input text is
read, not written.

## Data storage

- SQLite at `~/.grammar-ai/data.db`: settings (including the API key, stored in plaintext) and
  Polish history.
- Logs at `~/.grammar-ai/grammar_ai.log` (rotating, 10 MB) and `~/.grammar-ai/error.log`
  (startup-failure crash dump).

## Non-goals (current scope)

- No Linux or macOS support.
- No silent/automatic self-update (update check only, user opens the release page manually).
- No cloud sync of settings or history - everything is local to the machine.
- No support for elevated/protected target processes (UI Automation, like any unelevated caller,
  cannot read from or write to a window running at a higher integration level).

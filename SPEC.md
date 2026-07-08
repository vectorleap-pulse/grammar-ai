# Grammar AI - Specification

## Purpose

A free, lightweight Windows desktop utility that rewrites and translates text in place, in any
application, via a global hotkey. The user selects or focuses text anywhere in Windows, presses a
hotkey, and gets AI-generated results they can paste back without leaving the app they were in.

## Platform

Windows only. No browser extension, no Linux/macOS support at this time.

## Core features

### Polish

- Global hotkey (**Ctrl+Alt+S**) captures the focused control's text (selection if present,
  otherwise the full field) and sends it to the Polish tab.
- Rewrites the captured text into one or more **tones** (Professional, Casual, Chatting, Formal,
  Friendly, Empathetic, Assertive, Diplomatic), each generated for every configured **goal**
  (Inform, Persuade, Reassure, Motivate, Clarify, Apologize, Request, Acknowledge, Engage, Review,
  Clean) concurrently.
- Optional **cross-lingual polishing**: a configurable output language translates the source text
  before applying tone/goal rewriting.
- Each result has "Use" (paste back into the originating control) and "Copy" (explicit clipboard
  copy) actions. Alt+1 through Alt+9 and Alt+0 (app-level, only while the Polish tab has
  focus) trigger "Use" on the 1st through 10th result card, as a keyboard alternative to clicking.
- Every Polish result is saved to History (original text, polished text, tone, goal, timestamp).

### Translate

- Global hotkey (**Ctrl+Alt+D**) captures the focused control's text, into the Translate tab
  (see "Capture and paste-back mechanism" below).
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
- Background auto-update check against GitHub Releases: on finding a newer version, the installer
  is downloaded automatically to the user's Downloads folder, then a dismissible in-app banner
  offers to reveal it. "Update Now" opens Explorer with the installer selected - it is never
  executed by the app itself, only ever launched by an explicit user double-click.

## Capture and paste-back mechanism

**Both Polish and Translate capture** the focused control's text the same way: blank the
clipboard, simulate `Ctrl+C`, poll for the result (falling back to `Ctrl+A`, `Ctrl+C` if nothing
was already selected), then restore the clipboard's original contents.

- The clipboard-blank/simulate-`Ctrl+C`/poll/restore approach is structurally identical to
  clipboard-hijacking malware behavior and has been flagged as such by Bitdefender and likely
  other AV/EDR heuristics. This was originally a Translate-only trade-off, with Polish kept on
  UI-Automation-only capture (and paste-back) to avoid that risk; Polish was later migrated onto
  the same clipboard-based mechanism as Translate, for both capture and paste-back, trading that
  AV-heuristic risk for broader compatibility with apps that don't expose text via accessibility
  APIs, or whose UI Automation write support doesn't behave like a real user edit.
- `pyperclip` is also used, separately, for explicit user-clicked "Copy" buttons - a one-shot,
  user-initiated clipboard write, a different pattern from the programmatic capture/paste-back
  loops above.

**Polish's paste-back** ("Use") shares the same clipboard mechanism as capture: refocus the
original window, select-all + copy to read its *current* content (which may have changed since
capture), replace the captured original text with the polished result against that live read,
write the merged text to the clipboard, then select-all + paste. If the original window can't be
brought back to the real OS foreground (closed, or some other failure), Grammar AI falls back to
copying the result to the clipboard instead, so the user can paste manually.

**Translate** has no paste-back - its output is Copy-button-only.

Neither capture nor paste-back depends on Windows UI Automation any more (the `uiautomation`
package has been dropped from the project entirely); compatibility is now bounded only by whether
the target app supports standard `Ctrl+A`/`Ctrl+C`/`Ctrl+V` shortcuts, which is close to universal
for real text-editing surfaces.

## Data storage

- SQLite at `~/.grammar-ai/data.db`: settings (including the API key, stored in plaintext) and
  Polish history.
- Logs at `~/.grammar-ai/grammar_ai.log` (rotating, 10 MB) and `~/.grammar-ai/error.log`
  (startup-failure crash dump).

## Non-goals (current scope)

- No Linux or macOS support.
- No silent/automatic self-update: the installer is downloaded automatically, but never executed
  by the app itself - only ever launched by an explicit user double-click in Explorer. Deliberate:
  a process that downloads and then executes an unsigned binary itself is a common AV/EDR
  dropper-behavior heuristic trigger; requiring a human double-click is the same pattern browsers
  already use for downloaded files.
- No cloud sync of settings or history - everything is local to the machine.
- No support for elevated/protected target processes (simulated keystrokes, like any unelevated
  caller's input, cannot reach a window running at a higher integration level - UIPI blocks it).

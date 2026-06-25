# Grammar AI — Claude Code Guide

## Project overview

Desktop Windows app (Python 3.12 / Tkinter) that captures selected text via a global hotkey, sends it to an OpenAI-compatible LLM, and returns polished versions in a small UI. Runs in the system tray.

## How to run

```bash
uv sync
uv run python main.py
```

Build a standalone `.exe`:

```bash
uv sync --extra dev
python build.py          # release
python build.py --debug  # with console
```

## Architecture

```
main.py                   entry point — logging, DB init, i18n, MainWindow
app/
  config.py               constants: tones, goals, paths, hotkeys
  i18n.py                 lightweight i18n (Msg enum + translation tables for en/es/fr/de/ja/ko)
  schemas/models.py       Pydantic models: Tone, Goal, LLMConfig, PolishedText, HistoryEntry
  db/database.py          SQLite helpers (~/.grammar-ai/data.db)
  core/
    llm.py                prompt construction + OpenAI-compatible API call
    hotkey.py             global hotkey listener (keyboard lib)
    focus.py              focus restore + clipboard paste into source window
    autorun.py            Windows startup registration
    updater.py            GitHub release version check
  ui/
    main_window.py        root Tk window, tray, update bar
    main_tab.py           text input, tone selector, trigger, polished result cards
    settings_dialog.py    settings form (URL, model, key, language, goals, context)
    history_tab.py        paginated history browser
```

## Key conventions

- **i18n**: all UI strings go through `t(Msg.KEY)`. Add new keys to the `Msg` StrEnum *and* to every language dict in `_TRANSLATIONS`. English is the fallback (the enum value itself).
- **LLMConfig**: adding a field requires updating `load_config()` in `database.py` with a `.get()` default; `save_config()` uses `model_dump()` and picks it up automatically.
- **Tones** are selected one at a time; polishing produces one result **per goal** (not per tone).
- **Context field**: optional free-text; when non-empty it is appended to the system prompt as an "additional context" block that informs vocabulary and conventions without overriding grammar rules.
- Results are ordered by the `GOALS` list in `config.py`, inserted in that order as they stream in.
- History is stored on **Use** or **Copy**, not on every polish.
- `save_history()` takes `Tone` and `Goal` enum types (not plain strings).
- History detail view stores `(polished, original)` text in `HistoryTab._entry_texts` dict keyed by treeview `iid` — do not use treeview `tags` for data storage.

## LLM prompt structure

System prompt (built by `_build_system_prompt`):
1. HARD RULE — line endings (non-negotiable)
2. Role (language-aware writer persona)
3. Language rules
4. What to preserve
5. What NOT to do
6. Output format
7. *(if context set)* Additional context block

User message (built by `_format_batch_request`):
- Polish instruction with tone and list of goals
- Line-break count constraint
- JSON response format spec
- Input text wrapped in `<input_text>` tags
- *(chatting tone only)* extra contraction rules

Response is `{"goal": "polished text", ...}` JSON.

## Linting

```bash
uv run ruff check .
uv run mypy .
```

Line length limit: 100. Config in `pyproject.toml`.

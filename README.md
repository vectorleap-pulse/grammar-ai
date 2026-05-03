# GRAMMAR AI

## 1. Overview

**GRAMMAR AI** is a lightweight desktop application built with Python that provides AI-powered grammar correction and text rewriting. It operates primarily through clipboard interaction and hotkeys, offering a fast, system-wide writing assistant experience.

---

## 2. Goals

* Provide fast grammar correction and text polishing
* Support multiple tones (formal, casual, concise, etc.)
* Enable system-wide usage via clipboard + hotkeys
* Maintain a simple, compact UI
* Store usage history for reference and export

---

## 3. Tech Stack

### Core

* Python 3.12 (venv)
* tkinter (UI framework)

### Tooling

* Linter: `ruff` + `mypy`

  * Configured via `pyproject.toml`
  * Rule level: basic (no strict enforcement)
* Logger: `loguru`
* Schema validation: `pydantic`

### AI Integration

* OpenAI-compatible SDK (supports custom base URL)

  * Allows flexibility for:

    * OpenAI
    * Local LLMs
    * Proxy providers

### Dependency Management

* `requirements.txt`

---

## 4. Architecture

### High-Level Components

```
UI (tkinter)
│
├── Controller Layer
│   ├── LLM Service
│   ├── Clipboard Manager
│   ├── Hotkey Listener
│
├── Data Layer
│   ├── Config Store
│   ├── History Store
│
└── External
    └── LLM API (OpenAI-compatible)
```

---

## 5. Data Models (Pydantic)

### Config Schema

```python
class LLMConfig(BaseModel):
    base_url: str
    api_key: str
    model_name: str
```

### History Entry

```python
class HistoryEntry(BaseModel):
    id: int
    original_text: str
    polished_text: str
    tone: str
    timestamp: datetime
```

---

## 6. UI Design

## 6.1 General Style

* Compact layout
* Minimal padding
* Conventional desktop UI patterns
* Fast interaction (low animation / no heavy transitions)

---

## 6.2 Main Tab

### Components

#### 1. Toggle Section

* **On/Off Button**

  * Enables/disables background functionality

* **Settings Button**

  * Opens Settings Dialog

---

#### 2. Settings Dialog

Fields:

* Base URL
* API Key
* Model Name

Behavior:

* Validate all fields before saving
* Perform test API call (optional lightweight validation)
* Store config in database

---

#### 3. Input Section

* **Original Text (Editable Text Box)**

  * Pre-filled from clipboard or hotkey
  * User can modify before sending

---

#### 4. Action Section

* **Trigger Button**

  * Sends request to LLM
  * Input: original text
  * Output: multiple tone variations

---

#### 5. Output Section

* List of **Polished Text Items**

  * Each item:

    * Editable text field
    * Tone label (e.g., Formal, Casual, Concise)
    * **Use Button**

---

#### 6. Use Button Behavior

When clicked:

1. Simulate:

   * `Ctrl + A`
   * `Ctrl + V`
2. Replace content in currently focused input field
3. Save to history with timestamp

---

## 6.3 History Tab

### Components

* **History List**

  * Displays:

    * Original text
    * Polished text
    * Tone
    * Timestamp

* **Export Button**

  * Exports all history as Markdown

---

### Export Format (Markdown)

```markdown
## 2026-05-03 14:32

**Original:**
Hello how are you

**Polished (Formal):**
Hello, how are you?

---
```

---

## 7. Core Features

## 7.1 LLM Processing

### Input

* Original text

### Output

* Multiple variations:

  * Grammar corrected
  * Formal
  * Casual
  * Concise

### Prompt Strategy (example)

```
Fix grammar and provide variations in different tones:
- Formal
- Casual
- Concise

Return JSON format.
```

---

## 7.2 Clipboard + Hotkey System

### Hotkey1

**Shortcut:** `Ctrl + A → Ctrl + C → Trigger LLM`

Flow:

1. Select all text in focused field
2. Copy to clipboard
3. Send to LLM
4. Display results in UI

---

## 7.3 Clipboard Handling

* Monitor clipboard changes (optional passive mode)
* Primary trigger via hotkey
* Avoid processing:

  * Very short text
  * Non-text content

---

## 8. Storage

### Suggested: SQLite

#### Tables

**config**

* base_url
* api_key
* model_name

**history**

* id
* original_text
* polished_text
* tone
* timestamp

---

## 9. Logging

Using `loguru`:

* Log levels:

  * INFO: user actions
  * DEBUG: API requests
  * ERROR: failures

---

## 10. Error Handling

* Invalid API config → show alert
* API failure → retry option
* Empty input → disable trigger
* Clipboard failure → log + ignore

---

## 11. Performance Considerations

* Debounce trigger (avoid spam calls)
* Async LLM calls (threading or asyncio)
* Cache last result (optional)

---

## 12. Security Considerations

* Do not log API keys
* Mask sensitive data in logs
* Avoid processing:

  * Password-like strings
  * Very short tokens

---

## 13. Future Enhancements

* System tray mode
* Floating mini popup (like Grammarly)
* Multi-language support
* Local LLM fallback
* Plugin system for tone presets

---

## 14. Summary

GRAMMAR AI is designed as a fast, minimal, and extensible desktop writing assistant. By combining clipboard interaction, hotkeys, and LLM-based rewriting, it provides a practical alternative to browser-based tools while keeping implementation complexity manageable.

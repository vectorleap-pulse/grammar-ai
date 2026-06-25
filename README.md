<div align="center">

<img src="resources/icon.png" alt="Grammar AI" width="120" />

# Grammar AI

**A lightweight, FREE-forever desktop grammar corrector and text polisher.**

[![Latest Release](https://img.shields.io/github/v/release/vectorleap-pulse/grammar-ai?label=Download&color=blue&cacheSeconds=86400)](https://github.com/vectorleap-pulse/grammar-ai/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](https://github.com/vectorleap-pulse/grammar-ai/releases/latest)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)

</div>

---

## Overview

**Grammar AI** is a lightweight desktop application built with Python for grammar correction and text polishing. Tired of premium grammar tools like Grammarly and LanguageTool? Enjoy **FREE FOREVER** grammar correction with the free tier of the [Groq](https://groq.com/) API key. It provides a simple local UI for entering text, sending it to an AI service, and reviewing polished output.

It can also translate and polish text into the selected output language, so cross-lingual rewriting works naturally.

<div align="center">

![Usage demo](media/how-to-use.gif)

*Select text anywhere, press the hotkey, pick a polished version — done.*

</div>

---

## Highlights

| | |
|---|---|
| ⚡ **Fast** | Grammar correction and writing-style polishing in seconds |
| 🎭 **Multiple goals** | Generate variations for different writing goals — inform, persuade, clarify, and more |
| 🌍 **Cross-lingual** | Rewrite input into any chosen target language |
| 🆓 **Free forever** | Works with the Groq free-tier API key |
| 🕘 **History** | Every polished result is stored for later reference |
| 🪟 **Tray-native** | Runs quietly in the system tray, launches on startup |

---

## Usage

1. Launch the application. It runs in the system tray and starts automatically with Windows.
2. Configure your API settings in Settings (see [Configuration](#configuration)).
3. In Settings, choose which **goals** to generate (e.g. Inform, Persuade, Clarify) and optionally set a **context** to tailor output to your domain.
4. Enter or paste the text you want to polish.
5. Select a **tone** and press `Ctrl+Shift+Space` to capture selected text from any window, or use the **Trigger** button in the app.
6. Click the **Use** button next to the polished version you want to apply.

> 🎬 Prefer video? See [`media/how-to-use.mp4`](media/how-to-use.mp4) for the full walkthrough.

---

## Cross-lingual Polishing

Choose an output language in Settings and Grammar AI will translate any source language into it before polishing.

<div align="center">

<img src="media/cfg-output-langs.png" alt="Output language selection" width="420" />

*Pick from a curated list of output languages — or type any language the model understands.*

</div>

- The model translates any source language into the selected output language before polishing.
- If you choose **English**, the app polishes text using American English conventions.
- If you choose another language, the app writes polished text naturally in that language.

---

## Localized Interface

The whole interface is localized, so you can use Grammar AI in your own language.

<div align="center">

<img src="media/cfg-ui-langs.png" alt="Interface language selection" width="420" />

*Switch the interface language independently of the output language.*

</div>

<table>
  <tr>
    <td align="center">
      <img src="media/ui-spanish.png" alt="Spanish interface" width="320" /><br/>
      <sub><b>Español</b></sub>
    </td>
    <td align="center">
      <img src="media/ui-french.png" alt="French interface" width="320" /><br/>
      <sub><b>Français</b></sub>
    </td>
  </tr>
</table>

---

## Configuration

Grammar AI supports any LLM provider that is OpenAI-compatible, including OpenAI, Anthropic, Google, and more.

### Example Configuration ([Groq](https://groq.com/) Free Tier)

- **Base URL**: `https://api.groq.com/openai/v1/`
- **Model**: `meta-llama/llama-4-scout-17b-16e-instruct`
- **API Key**: `YOUR_GROQ_API_KEY`

### Example Configuration (OpenAI)

- **Base URL**: `https://api.openai.com/v1`
- **Model**: `gpt-4o-mini`
- **API Key**: `YOUR_OPENAI_API_KEY`

To configure:

1. Launch the application.
2. Open Settings and enter your API configuration.

---

## Installation

### Prebuilt Release (Windows)

**[⬇️ Download latest release →](https://github.com/vectorleap-pulse/grammar-ai/releases/latest)**

All releases: [github.com/vectorleap-pulse/grammar-ai/releases](https://github.com/vectorleap-pulse/grammar-ai/releases)

### From Source

1. Clone the repository.
2. Install dependencies: `uv sync`
3. Run: `uv run python main.py`

### Building from Source

To build a standalone executable:

1. Install dependencies including build tools: `uv sync --extra dev`
2. Run the build script:
   - Release build: `python build.py` or `build.bat`
   - Debug build (with console): `python build.py --debug` or `build.bat debug`
3. The executable will be created in the `build/grammar-ai/` folder.

---

## Tech Stack

- Python 3.12
- `tkinter` for UI
- `openai`-compatible AI integration
- `pystray` and `Pillow` for system tray
- `loguru` for logging
- `pydantic` for schema validation
- `ruff` and `mypy` for linting

---

## Storage

- Local SQLite database and log files are stored in `~/.grammar-ai/`.
- History entries include original text, polished text, tone, and timestamp.
- API keys are stored locally in the app database.

---

## Project Files

- `main.py` - application entry point
- `app/` - core application modules
- `pyproject.toml` - project metadata, dependencies, and linting configuration
- `build.py` - PyInstaller build script

---

## Support

If you found this helpful, please ⭐ **star this repository** and 👤 **follow me**!

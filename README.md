# Grammar AI

## Overview

**Grammar AI** is a lightweight desktop application built with Python for grammar correction and text polishing. Tired of premium grammar tools like Grammarly and LanguageTool? Enjoy **FREE FOREVER** grammar correction with the free tier of [Groq](https://groq.com/) API key. It provides a simple local UI for entering text, sending it to an AI service, and reviewing polished output.

---

## Usage

1. Launch the application. It runs in the system tray and starts automatically with Windows.
2. Configure your API settings in Settings (see Configuration section).
3. Enter or paste the text you want to polish.
4. Press `Ctrl+Shift+Space` to capture selected text from any window, or use the Trigger button in the app.
5. Click the **Use** button next to the polished version you want to apply.

![Usage demo](media/how-to-use.gif)

---

## Goals

* Provide fast grammar correction and writing-style polishing
* Offer multiple tone variations for output
* Keep the UI simple and easy to use
* Store history for future reference

---

## Tech Stack

* Python 3.12
* tkinter for UI
* `openai`-compatible AI integration
* `pystray` and `Pillow` for system tray
* `loguru` for logging
* `pydantic` for schema validation
* `ruff` and `mypy` for linting

---

## Configuration

Grammar AI supports any LLM provider that is OpenAI-compatible, including OpenAI, Anthropic, Google, and more.

### Example Configuration ([Groq](https://groq.com/) Free Tier)

- **Base URL**: `https://api.groq.com/openai/v1/`
- **Model**: `meta-llama/llama-4-scout-17b-16e-instruct`
- **API Key**: `YOUR_GROQ_API_KEY`

To configure:
1. Launch the application.
2. Open Settings and enter your API configuration.

---

## Installation

### Prebuilt Release (Windows)

Download the latest prebuilt executable for Windows from the [Releases](https://github.com/alpha5611331/grammar-ai/releases) page.

### From Source

1. Clone the repository.
2. Install dependencies: `pip install -e .`
3. Run: `python main.py`

### Building from Source

To build a standalone executable:

1. Install dependencies including build tools: `pip install -e ".[dev]"`
2. Run the build script:
   - Release build: `python build.py` or `build.bat`
   - Debug build (with console): `python build.py --debug` or `build.bat debug`
3. The executable will be created in the `dist/` folder.

---

## Storage

* Local SQLite database and log files are stored in `~/.grammar-ai/`.
* History entries include original text, polished text, tone, and timestamp.
* API keys are stored locally in the app database.

---

## Project Files

* `main.py` — application entry point
* `app/` — core application modules
* `pyproject.toml` — project metadata, dependencies, and linting configuration
* `build.py` — PyInstaller build script

---

## Support

If you found this helpful, please ⭐ star this repository and 👤 follow me!

---

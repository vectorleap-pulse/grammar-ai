# GRAMMAR AI

## Overview

GRAMMAR AI is a lightweight desktop application built with Python for grammar correction and text polishing. It provides a simple local UI for entering text, sending it to an AI service, and reviewing polished output.

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
* `loguru` for logging
* `pydantic` for schema validation
* `ruff` and `mypy` for linting

---

## Usage

1. Launch the application.
2. Enter or paste text into the main input area.
3. Click the trigger button to generate polished variations.
4. Review the results and copy the desired text.

---

## Storage

* Local SQLite database stores configuration and history.
* History entries include original text, polished text, tone, and timestamp.

---

## Project Files

* `main.py` — application entry point
* `app/` — core application modules
* `requirements.txt` — runtime dependencies
* `pyproject.toml` — linting and type-checking configuration

---

## Notes

* API keys are stored locally in the app database.
* The project is designed for minimal setup and straightforward use.

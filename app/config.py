import sys
from pathlib import Path

from app.schemas.models import Goal, Tone

APP_NAME = "Grammar AI"

_NUITKA_COMPILED: bool = "__compiled__" in globals()


def _frozen_base() -> Path:
    # PyInstaller 6+: data files live in _internal/ (sys._MEIPASS), not next to the exe.
    # Nuitka has no _MEIPASS; data files live next to the exe.
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else Path(sys.executable).parent


if getattr(sys, "frozen", False) or _NUITKA_COMPILED:
    ICON_PATH = _frozen_base() / "resources" / "icon.png"
else:
    ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "icon.png"

# Data storage
DATA_DIR = Path.home() / ".grammar-ai"
DB_PATH = DATA_DIR / "data.db"
LOG_PATH = DATA_DIR / "grammar_ai.log"
ERROR_LOG_PATH = DATA_DIR / "error.log"

# Cross-lingual polishing - output language for polished text.
# Maps the friendly label shown in Settings to the value passed to the model.
DEFAULT_OUTPUT_LANGUAGE = "English"
OUTPUT_LANGUAGES: dict[str, str] = {
    "English": "English",
    "Spanish (Español)": "Spanish",
    "French (Français)": "French",
    "German (Deutsch)": "German",
    "Italian (Italiano)": "Italian",
    "Portuguese (Português)": "Portuguese",
    "Dutch (Nederlands)": "Dutch",
    "Russian (Русский)": "Russian",
    "Ukrainian (Українська)": "Ukrainian",
    "Polish (Polski)": "Polish",
    "Turkish (Türkçe)": "Turkish",
    "Arabic (العربية)": "Arabic",
    "Hindi (हिन्दी)": "Hindi",
    "Chinese - Simplified (简体中文)": "Chinese (Simplified)",
    "Chinese - Traditional (繁體中文)": "Chinese (Traditional)",
    "Japanese (日本語)": "Japanese",
    "Korean (한국어)": "Korean",
    "Vietnamese (Tiếng Việt)": "Vietnamese",
    "Indonesian (Bahasa Indonesia)": "Indonesian",
}

# Interface localization - language of the app UI itself (distinct from output_language).
# Maps the friendly label shown in Settings to the i18n language code.
DEFAULT_UI_LANGUAGE = "en"
UI_LANGUAGES: dict[str, str] = {
    "English": "en",
    "Spanish (Español)": "es",
    "French (Français)": "fr",
    "German (Deutsch)": "de",
    "Japanese (日本語)": "ja",
    "Korean (한국어)": "ko",
}

# Text polishing
TONES: list[Tone] = [
    Tone.PROFESSIONAL,
    Tone.CASUAL,
    Tone.CHATTING,
    Tone.FORMAL,
    Tone.FRIENDLY,
    Tone.EMPATHETIC,
    Tone.ASSERTIVE,
    Tone.DIPLOMATIC,
]


GOAL_DESCRIPTIONS: dict[Goal, str] = {
    Goal.INFORM: "Present facts clearly and objectively",
    Goal.PERSUADE: "Convince the reader to adopt a viewpoint or take action",
    Goal.REASSURE: "Calm concerns and build confidence",
    Goal.MOTIVATE: "Inspire enthusiasm and drive action",
    Goal.CLARIFY: "Simplify and make the meaning unambiguous",
    Goal.APOLOGIZE: "Express regret and take responsibility",
    Goal.REQUEST: "Politely ask for action or information",
    Goal.ACKNOWLEDGE: "Validate the reader's point, effort, or feelings",
    Goal.ENGAGE: "Make the text more interesting and conversational",
    Goal.REVIEW: "Critically assess with balanced, constructive feedback",
    Goal.CLEAN: "Strip fluff and tighten to essential meaning",
}

GOALS: list[Goal] = list(GOAL_DESCRIPTIONS.keys())

GOALS_PRESET_MIN: list[Goal] = [Goal.INFORM, Goal.CLARIFY, Goal.CLEAN]
GOALS_PRESET_DEFAULT: list[Goal] = [
    Goal.INFORM,
    Goal.PERSUADE,
    Goal.REASSURE,
    Goal.MOTIVATE,
    Goal.CLARIFY,
]

# Global hotkey (RegisterHotKey combo - see app/core/hotkey.py)
HOTKEY: str = "Ctrl+Alt+S"
TRANSLATE_HOTKEY: str = "Ctrl+Alt+D"

# Auto-updater
RELEASES_API = "https://api.github.com/repos/vectorleap-pulse/grammar-ai/releases/latest"
UPDATE_CHECK_INTERVAL_MS = 5 * 60 * 1000

# Windows autorun
AUTORUN_REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# History
HISTORY_MAX_ENTRIES = 1000

# Main window
WINDOW_GEOMETRY = "360x640"
WINDOW_MIN_SIZE = (360, 480)
WINDOW_MAX_SIZE = (360, 720)

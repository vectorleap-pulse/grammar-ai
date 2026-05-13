import sys
from pathlib import Path

APP_NAME = "Grammar AI"

# Icon path — sys._MEIPASS when frozen, project root otherwise
if getattr(sys, "frozen", False):
    ICON_PATH = Path(getattr(sys, "_MEIPASS", ".")) / "resources" / "icon.png"
else:
    ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "icon.png"

# Data storage
DATA_DIR = Path.home() / ".grammar-ai"
DB_PATH = DATA_DIR / "data.db"
LOG_PATH = DATA_DIR / "grammar_ai.log"
ERROR_LOG_PATH = DATA_DIR / "error.log"

# Text polishing
TONES: list[str] = [
    "professional",
    "casual",
    "formal",
    "friendly",
    "empathetic",
    "assertive",
    "diplomatic",
]
GOALS: list[str] = ["inform", "persuade", "reassure", "motivate", "clarify"]

# Global hotkey
HOTKEYS: list[str] = ["ctrl", "shift", "space"]
HOTKEY: str = "+".join(HOTKEYS)

# Auto-updater
RELEASES_API = "https://api.github.com/repos/vectorleap-pulse/grammar-ai/releases/latest"
EXE_OLD_SUFFIX = "-old"
UPDATE_CHECK_INTERVAL_MS = 5 * 60 * 1000

# Windows autorun
AUTORUN_REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# History
HISTORY_MAX_ENTRIES = 1000

# Main window
WINDOW_GEOMETRY = "360x640"
WINDOW_MIN_SIZE = (360, 480)
WINDOW_MAX_SIZE = (360, 720)

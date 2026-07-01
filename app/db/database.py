import json
import sqlite3
from datetime import datetime, timezone

from loguru import logger

from app.config import DB_PATH, HISTORY_MAX_ENTRIES
from app.schemas.models import Goal, HistoryEntry, LLMConfig, Tone


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT NOT NULL,
                polished_text TEXT NOT NULL,
                tone          TEXT NOT NULL,
                goal          TEXT NOT NULL DEFAULT '',
                used_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        columns = [row[1] for row in conn.execute("PRAGMA table_info(history)").fetchall()]
        if "style" in columns and "goal" not in columns:
            conn.execute("ALTER TABLE history RENAME COLUMN style TO goal")
        elif "goal" not in columns:
            conn.execute("ALTER TABLE history ADD COLUMN goal TEXT NOT NULL DEFAULT ''")
    logger.info(f"Database initialized at {DB_PATH}")


def load_config() -> LLMConfig:
    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    data = {row["key"]: row["value"] for row in rows}
    return LLMConfig(
        base_url=data.get("base_url", "https://api.openai.com/v1"),
        model=data.get("model", "gpt-4o-mini"),
        api_key=data.get("api_key", ""),
        output_language=data.get("output_language", "English"),
        context=data.get("context", ""),
    )


def save_config(config: LLMConfig) -> None:
    with _connect() as conn:
        for key, value in config.model_dump().items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
    logger.info("Config saved")


def save_history(original: str, polished: str, tone: Tone, goal: Goal) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO history (original_text, polished_text, tone, goal) VALUES (?, ?, ?, ?)",
            (original, polished, tone, goal),
        )
        count = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        if count > HISTORY_MAX_ENTRIES:
            conn.execute("DELETE FROM history WHERE id = (SELECT MIN(id) FROM history)")
    logger.debug(f"History saved: tone={tone} goal={goal}")


def load_history(limit: int = 200, offset: int = 0) -> list[HistoryEntry]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY used_at DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
    return [
        HistoryEntry(
            id=row["id"],
            original_text=row["original_text"],
            polished_text=row["polished_text"],
            tone=row["tone"],
            goal=row["goal"] if "goal" in row.keys() else "",
            used_at=datetime.fromisoformat(row["used_at"])
            .replace(tzinfo=timezone.utc)
            .astimezone(),
        )
        for row in rows
    ]


def load_selected_tone() -> Tone:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'selected_tone'").fetchone()
    from app.config import TONES

    try:
        return Tone(row["value"]) if row else TONES[0]
    except ValueError:
        return TONES[0]


def save_selected_tone(tone: Tone) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('selected_tone', ?)",
            (tone,),
        )
    logger.debug(f"Selected tone saved: {tone}")


def clear_history() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM history")
    logger.info("History cleared")


def get_history_count() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM history").fetchone()
    return row["count"]


def load_selected_goals() -> list[Goal]:
    from app.config import GOALS, GOALS_PRESET_MIN

    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'selected_goals'").fetchone()
    if not row:
        return list(GOALS_PRESET_MIN)
    try:
        saved = set(json.loads(row["value"]))
        return [g for g in GOALS if g.value in saved]
    except Exception:
        return list(GOALS)


def save_selected_goals(goals: list[Goal]) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('selected_goals', ?)",
            (json.dumps(goals),),
        )
    logger.debug(f"Selected goals saved: {goals}")


def load_ui_language() -> str:
    from app.config import DEFAULT_UI_LANGUAGE

    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'ui_language'").fetchone()
    return row["value"] if row else DEFAULT_UI_LANGUAGE


def save_ui_language(code: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('ui_language', ?)",
            (code,),
        )
    logger.info(f"UI language saved: {code}")


def load_translate_language() -> str:
    from app.config import DEFAULT_OUTPUT_LANGUAGE

    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'translate_language'"
        ).fetchone()
    return row["value"] if row else DEFAULT_OUTPUT_LANGUAGE


def save_translate_language(label: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('translate_language', ?)",
            (label,),
        )
    logger.debug(f"Translate language saved: {label}")


def load_autorun() -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'autorun'").fetchone()
    return row["value"] == "1" if row else True


def save_autorun(enabled: bool) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('autorun', ?)",
            ("1" if enabled else "0",),
        )
    logger.info(f"Autorun setting saved: {enabled}")

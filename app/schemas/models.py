from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class Tone(StrEnum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    CHATTING = "chatting"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    EMPATHETIC = "empathetic"
    ASSERTIVE = "assertive"
    DIPLOMATIC = "diplomatic"


class Goal(StrEnum):
    INFORM = "inform"
    PERSUADE = "persuade"
    REASSURE = "reassure"
    MOTIVATE = "motivate"
    CLARIFY = "clarify"
    APOLOGIZE = "apologize"
    REQUEST = "request"
    ACKNOWLEDGE = "acknowledge"
    ENGAGE = "engage"
    REVIEW = "review"
    CLEAN = "clean"


class AppConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    output_language: str = "English"
    context: str = ""


class PolishedText(BaseModel):
    tone: Tone
    goal: Goal
    text: str


class HistoryEntry(BaseModel):
    id: int
    original_text: str
    polished_text: str
    tone: str
    goal: str = ""
    used_at: datetime

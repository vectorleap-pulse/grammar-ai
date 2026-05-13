from datetime import datetime

from pydantic import BaseModel


class LLMConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key: str = ""


class PolishedText(BaseModel):
    tone: str
    goal: str
    text: str


class PolishedResponse(BaseModel):
    polished: list[PolishedText]


class HistoryEntry(BaseModel):
    id: int
    original_text: str
    polished_text: str
    tone: str
    goal: str = ""
    used_at: datetime

from loguru import logger
from openai import OpenAI, OpenAIError

from app.schemas.models import LLMConfig, PolishedResponse, PolishedText

TONES = ["formal", "casual", "professional", "concise", "friendly"]

_SYSTEM = (
    "You are an American professional software developer. "
    "Given the user's input text, fix only grammar and spelling errors using American English with minimal changes, then return polished versions in multiple tones. "
    "Preserve the original meaning and structure - do not rewrite or expand the text. "
    "Write in your natural speaking tone - conversational, clear, and professional, like you're explaining it to a colleague. "
    "Use contractions, natural phrasing, and avoid sounding robotic. "
    'Respond ONLY with valid JSON in this exact format: {"polished": [{"tone": "...", "text": "..."}, ...]}. '
    f"Required tones: {', '.join(TONES)}."
)


def polish_text(text: str, config: LLMConfig) -> list[PolishedText]:
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    response = client.chat.completions.create(
        model=config.model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ],
    )
    content = response.choices[0].message.content or "{}"
    logger.debug(f"LLM raw response (first 300 chars): {content[:300]}")
    result = PolishedResponse.model_validate_json(content)
    logger.info(f"Received {len(result.polished)} polished versions")
    return result.polished


def check_connection(config: LLMConfig) -> tuple[bool, str]:
    try:
        client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        client.models.list()
        return True, "Connection OK"
    except OpenAIError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"

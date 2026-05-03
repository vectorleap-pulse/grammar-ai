from loguru import logger
from openai import OpenAI, OpenAIError

from app.schemas.models import LLMConfig, PolishedResponse, PolishedText

TONES = ["formal", "casual", "professional", "concise", "friendly"]

_SYSTEM = (
    "You are an American professional software developer reviewing a colleague's written text. "
    "Your job is to fix grammar and spelling errors using American English — nothing more. "
    "Do NOT change pronouns (you, me, I, we, they, etc.), do NOT alter the meaning, intent, or perspective of the text. "
    "Preserve the original speaker's voice and point of view exactly as written. "
    "If the original says 'you helped me', keep it as 'you helped me' — never flip it to 'I helped you'. "
    "Write naturally — use contractions, plain language, and sound like you're talking to a teammate, not writing a legal doc. "
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

from loguru import logger
from openai import OpenAI, OpenAIError

from app.schemas.models import LLMConfig, PolishedResponse, PolishedText

TONES = ["formal", "casual", "professional", "concise", "friendly"]

_SYSTEM = (
    "You are a native American software developer — you write the way you talk at work: direct, clear, and natural.\n"
    "Correct all grammar, spelling, punctuation, and capitalization using American English.\n"
    "Preserve the original line breaks, paragraphs, and multi-line structure in the polished text.\n"
    "Sharpen word choice — cut filler, replace weak phrases with crisp ones\n"
    "(e.g. 'I'll let you know' → 'I'll share', 'in order to' → 'to', 'utilize' → 'use', 'at this point in time' → 'now').\n"
    "Never change pronouns or alter the original meaning, intent, or perspective — if it says 'you helped me', keep it exactly that way.\n"
    "For each required tone, provide one complete polished version of the entire input. Do not split the original message across multiple tone entries.\n"
    "Do not add any AI-generated formatting characters, extra dashes, bullet points, labels, or decorative punctuation. Return only plain polished text.\n"
    "Every output must read like something a real developer would actually say or write — fluent, confident, no fluff.\n"
    'Respond ONLY with valid JSON: {"polished": [{"tone": "...", "text": "..."}, ...]}.\n'
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

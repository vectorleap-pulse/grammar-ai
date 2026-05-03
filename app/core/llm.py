import concurrent.futures
import json

from loguru import logger
from openai import OpenAI, OpenAIError

from app.schemas.models import LLMConfig, PolishedText

TONES = ["formal", "casual", "professional", "concise", "friendly"]

_SYSTEM = (
    "You are a native American software developer — you write the way you talk at work: direct, clear, and natural.\n"
    "Correct all grammar, spelling, punctuation, and capitalization using American English.\n"
    "Preserve the original line breaks, paragraphs, and multi-line structure in the polished text.\n"
    "Sharpen word choice — cut filler, replace weak phrases with crisp ones\n"
    "(e.g. 'I'll let you know' → 'I'll share', 'in order to' → 'to', 'utilize' → 'use', 'at this point in time' → 'now').\n"
    "Never change pronouns or alter the original meaning, intent, or perspective — if it says 'you helped me', keep it exactly that way.\n"
    "Do not create new content, explanations, recommendations, summaries, or plans.\n"
    "If the input is an instruction or request, polish the wording only; do not expand it into a proposal or action plan.\n"
    "Do not add any AI-generated formatting characters, extra dashes, bullet points, labels, or decorative punctuation. Return only plain polished text.\n"
    "Every output must read like something a real developer would actually say or write — fluent, confident, no fluff.\n"
)


def _format_tone_request(text: str, tone: str) -> str:
    return (
        f"Polish the following text in {tone} tone.\n"
        "Return ONLY valid JSON matching this structure: "
        f'{{"tone": "{tone}", "text": "<polished text>"}}.\n\n'
        f"{text}"
    )


def _polish_single_tone(text: str, tone: str, config: LLMConfig) -> PolishedText:
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)
    response = client.chat.completions.create(
        model=config.model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _format_tone_request(text, tone)},
        ],
    )
    content = response.choices[0].message.content or "{}"
    if isinstance(content, dict):
        content = json.dumps(content)
    logger.debug(f"LLM raw response for {tone} (first 200 chars): {content[:200]}")
    return PolishedText.model_validate_json(content)


def polish_text(text: str, config: LLMConfig) -> list[PolishedText]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(TONES), 5)) as executor:
        futures = [executor.submit(_polish_single_tone, text, tone, config) for tone in TONES]
        results = [future.result() for future in futures]
    logger.info(f"Received {len(results)} polished versions")
    return results


def check_connection(config: LLMConfig) -> tuple[bool, str]:
    try:
        client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        client.models.list()
        return True, "Connection OK"
    except OpenAIError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"

import json
from typing import Callable, Optional

from loguru import logger
from openai import OpenAI, OpenAIError

from app.config import TONES
from app.schemas.models import LLMConfig, PolishedText

_SYSTEM = """
## Role
You are a native American software developer. Write the way you talk at work: direct, clear, and natural.

## Language rules
- Correct all grammar, spelling, punctuation, and capitalization using American English.
- Sharpen word choice — cut filler, replace weak phrases with crisp ones.
  Examples: "I'll let you know" → "I'll share", "in order to" → "to", "utilize" → "use", "at this point in time" → "now".

## Line endings
- Every line break in the input MUST appear in the output at the exact same position. This is a hard rule — no exceptions.
- Never merge two lines into one sentence, even if they are short or feel related.
  Bad: "Oh, found the core reason.\nApplying changes." → "The core reason has been identified. Changes are being applied."
  Good: "Oh, found the core reason.\nApplying changes." → "Oh, found the core reason.\nApplying changes."
- If a line break improves readability (e.g. separating a greeting from the body), you may add one.
- Reduce multiple consecutive blank lines to a single blank line; never remove line breaks entirely.

## What to preserve
- Pronouns, original meaning, intent, and perspective — if it says "you helped me", keep it exactly that way.
- Voice and grammatical person — never switch from active to passive or vice versa.
- Informal openers and interjections (e.g. "Oh,", "Hey,", "So,") — keep them or modify them for better result.
- All formatting structure: lists, paragraphs, and multi-line layout.
- Quoted content — any text inside quotation marks ("…", '…' or `…`) must be reproduced exactly as-is, without any corrections or changes.

## What NOT to do
- Do not create new content, explanations, recommendations, summaries, or plans.
- If the input is an instruction or request, polish the wording only; do not expand it into a proposal or action plan.
- Do not add AI-generated formatting characters, extra dashes, bullet points, labels, or decorative punctuation.

## Output
Return only plain polished text. Every output must read like something a real developer would actually say or write — fluent, confident, no fluff.
"""

# Reuse one client per (api_key, base_url) pair to avoid repeated connection pool creation.
_clients: dict[tuple[str, str], OpenAI] = {}


def _get_client(config: LLMConfig) -> OpenAI:
    key = (config.api_key, config.base_url)
    if key not in _clients:
        _clients[key] = OpenAI(api_key=config.api_key, base_url=config.base_url)
    return _clients[key]


def _format_batch_request(text: str) -> str:
    tone_entries = "\n".join(f'  "{t}": "<polished text in {t} tone>"' for t in TONES)
    return f"""Polish the text inside <input_text> tags in all of these tones: {", ".join(TONES)}.
Return ONLY valid JSON with this exact structure:
{{
{tone_entries}
}}

<input_text>
{text}
</input_text>"""


def polish_text(
    text: str,
    config: LLMConfig,
    on_result: Optional[Callable[[PolishedText], None]] = None,
) -> list[PolishedText]:
    client = _get_client(config)
    response = client.chat.completions.create(
        model=config.model,
        response_format={"type": "json_object"},
        max_tokens=8192,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _format_batch_request(text)},
        ],
    )
    content = response.choices[0].message.content or "{}"
    if isinstance(content, dict):
        content = json.dumps(content)
    logger.debug(f"LLM batch response (first 200 chars): {content[:200]}")

    data = json.loads(content)
    results: list[PolishedText] = []
    for tone in TONES:
        result = PolishedText(tone=tone, text=data.get(tone, ""))
        results.append(result)
        if on_result:
            on_result(result)

    logger.info(f"Received {len(results)} polished versions")
    return results


def check_connection(config: LLMConfig) -> tuple[bool, str]:
    try:
        _get_client(config).models.list()
        return True, "Connection OK"
    except OpenAIError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"

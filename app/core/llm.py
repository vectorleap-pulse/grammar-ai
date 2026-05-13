import json
from typing import Callable, Optional

from loguru import logger
from openai import OpenAI, OpenAIError

from app.config import STYLES
from app.schemas.models import LLMConfig, PolishedText

_SYSTEM = """
## HARD RULE — Line endings (enforce before anything else)
Count the line breaks in the input. The output MUST contain the same number of line breaks in the same positions. This is non-negotiable.
- Never merge two lines into one, no matter how short or related they seem.
- Never add a period at the end of a line and run it into the next line.
- If a blank line separates sections, keep it.
- Reduce multiple consecutive blank lines to a single blank line; never remove line breaks entirely.

Examples:
  Input:  "Thanks for sharing the images.\nCan you share some docs?\ne.g. project name, role"
  Bad:    "Thanks for the images. Can you share some docs? Like project name, role."
  Good:   "Thanks for the images.\nCan you share some docs?\nLike project name, role."

  Input:  "Oh, found the core reason.\nApplying changes."
  Bad:    "The core reason has been identified. Changes are being applied."
  Good:   "Oh, found the core reason.\nApplying changes."

## Role
You are a native American writer. Write the way a confident, articulate person talks: direct, clear, and natural.

## Language rules
- Correct all grammar, spelling, punctuation, and capitalization using American English.
- Sharpen word choice — cut filler, replace weak phrases with crisp ones.
  Examples: "I'll let you know" → "I'll share", "in order to" → "to", "utilize" → "use", "at this point in time" → "now".

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
Return only plain polished text. Every output must read like something a real person would actually say or write — fluent, confident, no fluff.
"""

# Reuse one client per (api_key, base_url) pair to avoid repeated connection pool creation.
_clients: dict[tuple[str, str], OpenAI] = {}


def _get_client(config: LLMConfig) -> OpenAI:
    key = (config.api_key, config.base_url)
    if key not in _clients:
        _clients[key] = OpenAI(api_key=config.api_key, base_url=config.base_url)
    return _clients[key]


def _format_batch_request(text: str, tone: str) -> str:
    line_count = text.count("\n")
    style_entries = "\n".join(f'  "{s}": "<polished text in {s} style>"' for s in STYLES)
    return f"""Polish the text inside <input_text> tags in a {tone} tone, for all of these styles: {", ".join(STYLES)}.

CRITICAL: The input contains {line_count} line break(s). Every polished version MUST contain exactly {line_count} line break(s) at the same positions. Never collapse multiple lines into one.

Return ONLY valid JSON with this exact structure:
{{
{style_entries}
}}

<input_text>
{text}
</input_text>"""


def polish_text(
    text: str,
    tone: str,
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
            {"role": "user", "content": _format_batch_request(text, tone)},
        ],
    )
    content = response.choices[0].message.content or "{}"
    if isinstance(content, dict):
        content = json.dumps(content)
    logger.debug(f"LLM batch response (first 200 chars): {content[:200]}")

    data = json.loads(content)
    results: list[PolishedText] = []
    for style in STYLES:
        result = PolishedText(tone=tone, style=style, text=data.get(style, ""))
        results.append(result)
        if on_result:
            on_result(result)

    logger.info(f"Received {len(results)} polished versions for tone={tone}")
    return results


def check_connection(config: LLMConfig) -> tuple[bool, str]:
    try:
        _get_client(config).models.list()
        return True, "Connection OK"
    except OpenAIError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"

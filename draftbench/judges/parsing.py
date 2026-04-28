"""Robust JSON extraction from LLM judge responses.

LLMs return JSON in three flavors:
  1. Plain JSON:                     `{"score": 4, ...}`
  2. JSON inside a code block:       ```json\n{"score": 4, ...}\n```
  3. JSON with a prose preamble:     `Here is my evaluation:\n{"score": 4, ...}`

This module handles all three robustly so the judge framework doesn't break on
prompt-following variance across models.
"""

from __future__ import annotations

import json
import re
from typing import Any

CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_judge_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from an LLM response.

    Tries (in order):
      1. ```json …``` code blocks
      2. Direct `json.loads` on the whole stripped string
      3. The first balanced `{...}` substring

    Raises `ValueError` if no parse succeeds.
    """
    if not text or not text.strip():
        raise ValueError("Empty judge response")

    # 1) Code block
    m = CODE_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 2) Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 3) First balanced {...}
    start = text.find("{")
    if start >= 0:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not extract JSON from response: {text[:200]!r}")

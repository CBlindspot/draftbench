"""OpenRouter adapter — single API key, unified pricing, broad model coverage.

OpenRouter's OpenAI-compatible endpoint reaches every frontier model through
one billing account: Claude (Opus / Sonnet / Haiku), GPT-5.4, Llama 3.3,
Llama 4 Maverick, Deepseek R1 / V3.2, Qwen 3 Max Thinking, Qwen 3.6 Plus,
Hermes 3 405B. Per-model pricing is passed in at construction.

See `scripts/refresh_pricing.py` to fetch the current per-model rates from
OpenRouter's `/api/v1/models` endpoint.
"""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from draftbench.models.base import BaseModelAdapter, GenerationConfig


class OpenRouterAdapter(BaseModelAdapter):
    """Talks to OpenRouter's OpenAI-compatible chat-completions endpoint."""

    def __init__(
        self,
        model: str,
        pricing_in: float,
        pricing_out: float,
        display_name: str | None = None,
    ):
        super().__init__(
            model_name=display_name or model,
            pricing_per_1m_in_usd=pricing_in,
            pricing_per_1m_out_usd=pricing_out,
        )
        self.openrouter_model = model
        self._client: OpenAI | None = None

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise RuntimeError("OPENROUTER_API_KEY not set in environment")
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": os.environ.get(
                        "OPENROUTER_REFERER", "https://github.com/cblindspot/draftbench"
                    ),
                    "X-Title": os.environ.get("OPENROUTER_TITLE", "DraftBench"),
                },
            )
        return self._client

    def is_available(self) -> bool:
        return bool(os.environ.get("OPENROUTER_API_KEY"))

    def generate(
        self,
        system: str,
        user: str,
        config: GenerationConfig | None = None,
    ) -> tuple[str, int, int, dict[str, Any]]:
        cfg = config or GenerationConfig()
        client = self._ensure_client()
        response = client.chat.completions.create(
            model=self.openrouter_model,
            max_tokens=cfg.max_output_tokens,
            temperature=cfg.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        output = response.choices[0].message.content or ""
        usage = response.usage
        tin = usage.prompt_tokens if usage else 0
        tout = usage.completion_tokens if usage else 0
        raw = {
            "id": response.id,
            "finish_reason": response.choices[0].finish_reason,
            # OpenRouter routes to a specific upstream provider per call; record
            # the resolved model so we can audit variance across runs.
            "model_used": response.model,
        }
        return output, tin, tout, raw

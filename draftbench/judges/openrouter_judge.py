"""OpenRouter-backed judge.

Uses the same OpenAI-compatible endpoint as the generator-side adapter, but
constrains output to JSON via the prompt and parses robustly.

Retries on transient errors (429 / 408 / 5xx) with exponential backoff per
METHODOLOGY.md §7 testing parameters. 4xx business errors (auth, bad request)
short-circuit immediately — retrying them is pointless and can mask real bugs.
"""

from __future__ import annotations

import os
import time
from typing import Any

from openai import OpenAI

from draftbench.judges.base import BaseJudge, JudgeConfig, JudgeFinding, JudgeResult
from draftbench.judges.parsing import parse_judge_json

JUDGE_MAX_RETRIES = 30
BASE_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 30.0


class OpenRouterJudge(BaseJudge):
    """Judge that calls a model via OpenRouter and parses a JSON verdict."""

    def __init__(
        self,
        model: str,
        pricing_in: float,
        pricing_out: float,
        display_name: str | None = None,
        max_retries: int = JUDGE_MAX_RETRIES,
    ):
        self.openrouter_model = model
        self.judge_model = display_name or model
        self.pricing_in = pricing_in
        self.pricing_out = pricing_out
        self.max_retries = max_retries
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

    def judge(
        self,
        system_prompt: str,
        user_prompt: str,
        config: JudgeConfig | None = None,
    ) -> JudgeResult:
        cfg = config or JudgeConfig()
        t0 = time.monotonic()
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                client = self._ensure_client()
                response = client.chat.completions.create(
                    model=self.openrouter_model,
                    max_tokens=cfg.max_output_tokens,
                    temperature=cfg.temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                text = response.choices[0].message.content or ""
                usage = response.usage
                tin = usage.prompt_tokens if usage else 0
                tout = usage.completion_tokens if usage else 0
                cost = (tin / 1_000_000) * self.pricing_in + (tout / 1_000_000) * self.pricing_out
                latency_ms = int((time.monotonic() - t0) * 1000)

                verdict = parse_judge_json(text)
                raw_score = int(verdict.get("score", 0))
                score = max(0.0, min(1.0, (raw_score - 1) / 4.0)) if 1 <= raw_score <= 5 else 0.0
                findings = [
                    _to_finding(f) for f in verdict.get("findings", []) if isinstance(f, dict)
                ]
                rationale = str(verdict.get("rationale", "")).strip()

                return JudgeResult(
                    score=score,
                    raw_score=raw_score,
                    findings=findings,
                    rationale=rationale,
                    judge_model=self.judge_model,
                    cost_usd=round(cost, 6),
                    latency_ms=latency_ms,
                    raw_response={
                        "id": response.id,
                        "finish_reason": response.choices[0].finish_reason,
                        "model_used": response.model,
                        "raw_text": text,
                        "attempts": attempt,
                    },
                )
            except Exception as exc:  # noqa: BLE001 — tag, retry, or surface
                last_exc = exc
                # Don't retry 4xx business errors except 408/429.
                status = getattr(exc, "status_code", None) or getattr(
                    getattr(exc, "response", None), "status_code", None
                )
                if status and 400 <= status < 500 and status not in (408, 429):
                    break
                if attempt < self.max_retries:
                    backoff = min(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)), MAX_BACKOFF_SECONDS)
                    time.sleep(backoff)

        latency_ms = int((time.monotonic() - t0) * 1000)
        exc_type = type(last_exc).__name__ if last_exc else "Unknown"
        return JudgeResult(
            score=0.0,
            raw_score=0,
            judge_model=self.judge_model,
            latency_ms=latency_ms,
            error=f"{exc_type}: {last_exc}",
        )


def _to_finding(raw: dict[str, Any]) -> JudgeFinding:
    return JudgeFinding(
        issue=str(raw.get("issue", "")),
        severity=str(raw.get("severity", "minor")).lower(),
        location=str(raw.get("location", "n/a")),
        explanation=str(raw.get("explanation", "")),
    )

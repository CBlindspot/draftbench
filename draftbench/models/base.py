"""Base adapter contract — every model conforms to one interface."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from draftbench.config import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_RETRIES,
    DEFAULT_TEMPERATURE_NON_REASONING,
)

BASE_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 30.0


@dataclass
class GenerationConfig:
    """Per-call generation parameters."""

    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    temperature: float = DEFAULT_TEMPERATURE_NON_REASONING


@dataclass
class GenerationResult:
    """Output of a single drafting call — one model, one invention, one repeat."""

    model_name: str
    invention_id: str
    output_text: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    retry_count: int = 0

    @property
    def succeeded(self) -> bool:
        return self.error is None and bool(self.output_text)


class BaseModelAdapter(ABC):
    """Abstract adapter. Every concrete model — direct API, browser-driven, or
    cached response — implements `generate()` and `is_available()`."""

    model_name: str = "unknown"

    def __init__(
        self,
        model_name: str | None = None,
        pricing_per_1m_in_usd: float = 0.0,
        pricing_per_1m_out_usd: float = 0.0,
    ):
        if model_name is not None:
            self.model_name = model_name
        self.pricing_in = pricing_per_1m_in_usd
        self.pricing_out = pricing_per_1m_out_usd

    @abstractmethod
    def generate(
        self,
        system: str,
        user: str,
        config: GenerationConfig | None = None,
    ) -> tuple[str, int, int, dict[str, Any]]:
        """Call the underlying system. Returns (output_text, tokens_in, tokens_out, raw_response)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the system is reachable / authenticated."""

    def draft(
        self,
        invention_id: str,
        system: str,
        user: str,
        config: GenerationConfig | None = None,
        retries: int = DEFAULT_RETRIES,
    ) -> GenerationResult:
        """Wrap `generate()` with timing, retries, and cost computation."""
        cfg = config or GenerationConfig()
        t0 = time.monotonic()
        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                output, tin, tout, raw = self.generate(system, user, cfg)
                latency_ms = int((time.monotonic() - t0) * 1000)
                cost = (tin / 1_000_000) * self.pricing_in + (tout / 1_000_000) * self.pricing_out
                return GenerationResult(
                    model_name=self.model_name,
                    invention_id=invention_id,
                    output_text=output,
                    latency_ms=latency_ms,
                    tokens_in=tin,
                    tokens_out=tout,
                    cost_usd=round(cost, 6),
                    raw_response=raw,
                    retry_count=attempt - 1,
                )
            except Exception as exc:  # noqa: BLE001 — tag, don't crash the batch
                last_exc = exc
                # Don't retry 4xx business errors (auth, bad request) except 408/429.
                status = getattr(exc, "status_code", None) or getattr(
                    getattr(exc, "response", None), "status_code", None
                )
                if status and 400 <= status < 500 and status not in (408, 429):
                    break
                if attempt < retries:
                    backoff = min(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)), MAX_BACKOFF_SECONDS)
                    time.sleep(backoff)

        latency_ms = int((time.monotonic() - t0) * 1000)
        exc_type = type(last_exc).__name__ if last_exc else "Unknown"
        return GenerationResult(
            model_name=self.model_name,
            invention_id=invention_id,
            output_text="",
            latency_ms=latency_ms,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            error=f"{exc_type}: {last_exc}",
            retry_count=retries,
        )

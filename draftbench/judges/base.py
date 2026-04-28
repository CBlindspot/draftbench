"""Base judge contract — every layer-specific judge wraps a BaseJudge."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JudgeConfig:
    """Per-call judge generation parameters.

    Defaults to deterministic temperature 0.0 — judges should not be creative.
    """

    temperature: float = 0.0
    max_output_tokens: int = 4096


@dataclass
class JudgeFinding:
    """One specific issue identified by the judge."""

    issue: str
    severity: str  # "critical" | "major" | "minor"
    location: str  # section + line snippet, or "n/a"
    explanation: str


@dataclass
class JudgeResult:
    """Full output of a single judge call.

    `score` is normalized to 0.0-1.0 for downstream composite math.
    `raw_score` preserves the 1-5 scale the judge actually emitted.
    """

    score: float
    raw_score: int
    findings: list[JudgeFinding] = field(default_factory=list)
    rationale: str = ""
    judge_model: str = ""
    cost_usd: float = 0.0
    latency_ms: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


class BaseJudge(ABC):
    """Abstract judge — concrete impls call out to LLM providers (OpenRouter, etc.)."""

    judge_model: str = "unknown"

    @abstractmethod
    def judge(
        self,
        system_prompt: str,
        user_prompt: str,
        config: JudgeConfig | None = None,
    ) -> JudgeResult:
        """Run the judge on a (system, user) prompt pair, return a parsed JudgeResult."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the judge backend is reachable / authenticated."""

"""DraftBench — open-source benchmark for AI-assisted patent drafting."""

from __future__ import annotations

from draftbench.config import BenchmarkConfig, EvaluationLayer
from draftbench.harness import BenchmarkResults, BenchmarkRunner
from draftbench.metrics import summarize_auto_metrics
from draftbench.models.base import BaseModelAdapter, GenerationConfig
from draftbench.prompts import DRAFTING_SYSTEM_PROMPT, build_user_prompt

__version__ = "0.1.0"

__all__ = [
    "BaseModelAdapter",
    "BenchmarkConfig",
    "BenchmarkResults",
    "BenchmarkRunner",
    "DRAFTING_SYSTEM_PROMPT",
    "EvaluationLayer",
    "GenerationConfig",
    "build_user_prompt",
    "summarize_auto_metrics",
]

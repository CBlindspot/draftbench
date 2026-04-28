"""Model adapters — pluggable backends for the benchmark harness."""

from __future__ import annotations

from draftbench.models.base import BaseModelAdapter, GenerationConfig, GenerationResult
from draftbench.models.openrouter_adapter import OpenRouterAdapter

__all__ = [
    "BaseModelAdapter",
    "GenerationConfig",
    "GenerationResult",
    "OpenRouterAdapter",
]

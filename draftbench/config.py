"""Configuration objects for benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvaluationLayer(str, Enum):
    """Layers from METHODOLOGY.md §6."""

    STRUCTURAL = "structural"  # Layer 1 — MPEP 608.01, regex + parser, no LLM
    SECTION_112_US = "section_112_us"  # Layer 2 — §112 US, LLM-judge cross-family
    HUMAN_PANEL = "human_panel"  # Layer 3 — reserved for blind review (no automation)
    JURISDICTIONAL = "jurisdictional"  # Layer 4 — EP/CN/JP, LLM-judge
    HALLUCINATION = "hallucination"  # Layer 5 — 5-class taxonomy + Therasense kill-switch


# Aligned with Artificial Analysis Intelligence Index v4.0.4.
DEFAULT_TEMPERATURE_NON_REASONING = 0.0
DEFAULT_TEMPERATURE_REASONING = 0.6
DEFAULT_MAX_OUTPUT_TOKENS = 16384
DEFAULT_RETRIES = 30


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run.

    Defaults match METHODOLOGY.md §7 testing parameters.
    """

    repeats: int = 3
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    temperature: float = DEFAULT_TEMPERATURE_NON_REASONING
    retries: int = DEFAULT_RETRIES
    enabled_layers: tuple[EvaluationLayer, ...] = (
        EvaluationLayer.STRUCTURAL,
    )  # v1.0 ships Layer 1 live; Layers 2/4/5 LLM-judge in Phase 2

    def is_layer_enabled(self, layer: EvaluationLayer) -> bool:
        return layer in self.enabled_layers

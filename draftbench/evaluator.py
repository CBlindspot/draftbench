"""Layered evaluator — wraps Layer 1 auto-metrics; placeholders for Layers 2/4/5.

Layer 1 (structural) is live in v1.0. Layers 2 (§112 US LLM-judge), 4
(jurisdictional EP/CN/JP LLM-judge), and 5 (hallucination 5-class taxonomy +
Therasense kill-switch) are scoped to Phase 2 of the IMPLEMENTATION_CHECKLIST.

Until Phase 2 lands, calling `evaluate()` only populates Layer 1 fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from draftbench.config import BenchmarkConfig, EvaluationLayer
from draftbench.metrics import summarize_auto_metrics


@dataclass
class LayerScore:
    layer: EvaluationLayer
    score: float  # 0.0 - 1.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DraftEvaluation:
    invention_id: str
    model_name: str
    layer_scores: list[LayerScore] = field(default_factory=list)


class DeterministicEvaluator:
    """Layer 1 evaluator — regex + parser, no LLM call.

    Scores: 1.0 if all three sections are present and the abstract is within
    the 150-word MPEP limit; partial credit otherwise. This is a coarse signal
    by design — strategic claim quality (Dim 1) and §112 conformance (Dim 2)
    require Layer 2-5 evaluators, not Layer 1.
    """

    def evaluate(self, draft_output: str) -> LayerScore:
        metrics = summarize_auto_metrics(draft_output)
        # Three required sections + abstract within limit + at least one independent claim.
        checks = [
            metrics["has_abstract"],
            metrics["has_claims"],
            metrics["has_specification"],
            metrics["abstract_within_150w"],
            metrics["claims"]["independent"] >= 1,
        ]
        score = sum(1 for c in checks if c) / len(checks)
        return LayerScore(layer=EvaluationLayer.STRUCTURAL, score=score, details=metrics)


class LayeredEvaluator:
    """Composite evaluator that runs the layers enabled in `BenchmarkConfig.enabled_layers`.

    v1.0 wires only Layer 1. Phase 2 will register Layer 2 / 4 / 5 LLM-judge
    handlers here.
    """

    def __init__(self, config: BenchmarkConfig | None = None):
        self.config = config or BenchmarkConfig()
        self._layer1 = DeterministicEvaluator()

    def evaluate_draft(
        self,
        invention_id: str,
        model_name: str,
        draft_output: str,
    ) -> DraftEvaluation:
        scores: list[LayerScore] = []
        if self.config.is_layer_enabled(EvaluationLayer.STRUCTURAL):
            scores.append(self._layer1.evaluate(draft_output))
        # Layer 2 / 4 / 5 — Phase 2.
        return DraftEvaluation(
            invention_id=invention_id,
            model_name=model_name,
            layer_scores=scores,
        )

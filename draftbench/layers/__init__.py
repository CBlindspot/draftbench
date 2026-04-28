"""Layered evaluators — METHODOLOGY.md §6.

Layer 1 (structural)         → `draftbench.metrics` + `draftbench.evaluator.DeterministicEvaluator`
Layer 2 (§112 US LLM-judge)  → `draftbench.layers.section_112_us`
Layer 3 (human panel)        → `draftbench.blind_review` (export only — no automation)
Layer 4 (jurisdictional)     → `draftbench.layers.jurisdictional` (Phase 2 follow-up)
Layer 5A (Therasense)        → `draftbench.layers.therasense`
Layer 5B (hallucination B-E) → `draftbench.layers.hallucination` (Phase 2 follow-up)
"""

from __future__ import annotations

from draftbench.layers.hallucination import (
    HallucinationTaxonomyJudge,
    HallucinationTaxonomyResult,
    TaxonomyFinding,
)
from draftbench.layers.jurisdictional import JurisdictionalEvaluation, JurisdictionalJudge
from draftbench.layers.section_112_us import Section112USEvaluation, Section112USJudge
from draftbench.layers.therasense import TheresenseChecker, TheresenseResult

__all__ = [
    "HallucinationTaxonomyJudge",
    "HallucinationTaxonomyResult",
    "JurisdictionalEvaluation",
    "JurisdictionalJudge",
    "Section112USEvaluation",
    "Section112USJudge",
    "TaxonomyFinding",
    "TheresenseChecker",
    "TheresenseResult",
]

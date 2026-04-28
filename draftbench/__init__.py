"""DraftBench — open-source benchmark for AI-assisted patent drafting."""

from __future__ import annotations

from draftbench.config import BenchmarkConfig, EvaluationLayer
from draftbench.harness import BenchmarkResults, BenchmarkRunner
from draftbench.judges.base import BaseJudge, JudgeConfig, JudgeFinding, JudgeResult
from draftbench.judges.openrouter_judge import OpenRouterJudge
from draftbench.layers.hallucination import (
    HallucinationTaxonomyJudge,
    HallucinationTaxonomyResult,
    TaxonomyFinding,
)
from draftbench.layers.jurisdictional import JurisdictionalEvaluation, JurisdictionalJudge
from draftbench.layers.section_112_us import Section112USEvaluation, Section112USJudge
from draftbench.layers.therasense import TheresenseChecker, TheresenseResult
from draftbench.metrics import summarize_auto_metrics
from draftbench.models.base import BaseModelAdapter, GenerationConfig
from draftbench.prompts import DRAFTING_SYSTEM_PROMPT, build_user_prompt
from draftbench.scoring.composite import (
    DIMENSION_WEIGHTS,
    CompositeScore,
    CompositeScorer,
    DimensionScore,
)
from draftbench.scoring.report import HTMLReportGenerator
from draftbench.uspto import USPTOClient, VerificationResult

__version__ = "0.1.0"

__all__ = [
    "BaseJudge",
    "BaseModelAdapter",
    "BenchmarkConfig",
    "BenchmarkResults",
    "BenchmarkRunner",
    "CompositeScore",
    "CompositeScorer",
    "DIMENSION_WEIGHTS",
    "DRAFTING_SYSTEM_PROMPT",
    "DimensionScore",
    "EvaluationLayer",
    "GenerationConfig",
    "HTMLReportGenerator",
    "HallucinationTaxonomyJudge",
    "HallucinationTaxonomyResult",
    "JudgeConfig",
    "JudgeFinding",
    "JudgeResult",
    "JurisdictionalEvaluation",
    "JurisdictionalJudge",
    "OpenRouterJudge",
    "Section112USEvaluation",
    "Section112USJudge",
    "TaxonomyFinding",
    "TheresenseChecker",
    "TheresenseResult",
    "USPTOClient",
    "VerificationResult",
    "build_user_prompt",
    "summarize_auto_metrics",
]

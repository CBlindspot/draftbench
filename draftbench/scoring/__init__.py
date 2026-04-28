"""Composite scoring + HTML report — METHODOLOGY.md §3, §12."""

from __future__ import annotations

from draftbench.scoring.composite import (
    DIMENSION_WEIGHTS,
    CompositeScore,
    CompositeScorer,
    DimensionScore,
)
from draftbench.scoring.report import HTMLReportGenerator

__all__ = [
    "DIMENSION_WEIGHTS",
    "CompositeScore",
    "CompositeScorer",
    "DimensionScore",
    "HTMLReportGenerator",
]

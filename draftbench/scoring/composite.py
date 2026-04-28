"""Composite scorer — METHODOLOGY.md §3-4.

Combines the 7 weighted dimensions into a single 0.0-1.0 composite score.
Track A (60%) requires the historical-corpus pipeline, deferred to v1.1.
Track B (40%) requires the human panel. Most v1.0 INTA-time scoring is
therefore "partial" — only Dims 1 (auto Layer 1 signal), 2 (Layer 2 US +
Layer 4 EP/CN/JP), and 5 (Layer 5A Therasense + Layer 5B taxonomy) are
covered without external dependencies.

Therasense kill-switch (Class A → fabricated citation → instant fail) is the
non-negotiable hard floor: composite = 0.0 regardless of all other dimensions.

Per-dimension weights (METHODOLOGY.md §4):
  Dim 1 Claim Drafting Quality   35%
  Dim 2 Specification Quality    20%
  Dim 3 Durability               15%   (Track A — deferred to v1.1)
  Dim 4 Workflow & UX            10%   (Track B — deferred to v1.1)
  Dim 5 Safety / Fabrication     10%
  Dim 6 Confidentiality / Trust   5%   (vendor metadata, captured separately)
  Dim 7 Integration & TCO         5%   (vendor metadata, captured separately)

Dim 2 sub-weights (METHODOLOGY.md §4.1):
  US 0.5  EP 0.2  CN 0.15  JP 0.15  → Layer 2 supplies US, Layer 4 supplies the rest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from draftbench.layers.hallucination import HallucinationTaxonomyResult
    from draftbench.layers.jurisdictional import JurisdictionalEvaluation
    from draftbench.layers.section_112_us import Section112USEvaluation
    from draftbench.layers.therasense import TheresenseResult


DIMENSION_WEIGHTS: dict[int, float] = {
    1: 0.35,
    2: 0.20,
    3: 0.15,
    4: 0.10,
    5: 0.10,
    6: 0.05,
    7: 0.05,
}

# Dim 2 sub-weights (US handled by Layer 2; non-US handled by Layer 4).
DIM2_US_WEIGHT = 0.5
DIM2_NON_US_WEIGHT = 0.5

# Dim 5 sub-weights — Class A (kill-switch) is binary; Classes B-E carry the gradient.
DIM5_CLASS_A_WEIGHT = 0.5
DIM5_CLASSES_BE_WEIGHT = 0.5

# Dimensions deferred to later versions or out of per-draft scoring scope.
DEFERRED_DIMENSIONS: dict[int, str] = {
    3: "Track A corpus pending — deferred to v1.1",
    4: "Track B attorney edit-time — deferred to v1.1",
    6: "Vendor metadata — captured separately at vendor onboarding",
    7: "Vendor metadata — captured separately at vendor onboarding",
}


@dataclass
class DimensionScore:
    """Score + provenance for a single dimension on a single draft."""

    dimension: int
    weight: float
    score: float | None  # 0.0-1.0; None when the dimension is deferred / out of scope
    sources: list[str] = field(default_factory=list)  # which layers contributed
    note: str = ""  # explanation for None / partial scores


@dataclass
class CompositeScore:
    """Final composite score for one draft."""

    invention_id: str
    model_name: str
    composite: float  # 0.0-1.0; reflects available dimensions
    coverage: float  # fraction of total weight covered by scored dimensions
    extrapolated_composite: float  # composite / coverage — full-scale projection
    dimension_scores: dict[int, DimensionScore] = field(default_factory=dict)
    kill_switch_active: bool = False
    kill_switch_reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class CompositeScorer:
    """Combines per-layer evaluations into a CompositeScore.

    All inputs are optional — pass `None` when a layer wasn't run. The scorer
    will note the omission in the returned `CompositeScore.notes`.
    """

    def score(
        self,
        invention_id: str,
        model_name: str,
        *,
        layer1_metrics: dict | None = None,
        section_112_us: Section112USEvaluation | None = None,
        jurisdictional: JurisdictionalEvaluation | None = None,
        therasense: TheresenseResult | None = None,
        hallucination_taxonomy: HallucinationTaxonomyResult | None = None,
    ) -> CompositeScore:
        dim_scores: dict[int, DimensionScore] = {}
        notes: list[str] = []

        # Dim 1 — Claim Drafting Quality. Layer 1 only provides a coarse structural signal;
        # full Dim 1 needs the panel (Track B). Report partial signal with note.
        dim_scores[1] = self._dim1_score(layer1_metrics, notes)

        # Dim 2 — Specification Quality. US half from Layer 2, non-US half from Layer 4.
        dim_scores[2] = self._dim2_score(section_112_us, jurisdictional, notes)

        # Dim 3 — Durability. Track A only.
        dim_scores[3] = DimensionScore(
            dimension=3,
            weight=DIMENSION_WEIGHTS[3],
            score=None,
            note=DEFERRED_DIMENSIONS[3],
        )

        # Dim 4 — Workflow & UX. Track B only.
        dim_scores[4] = DimensionScore(
            dimension=4,
            weight=DIMENSION_WEIGHTS[4],
            score=None,
            note=DEFERRED_DIMENSIONS[4],
        )

        # Dim 5 — Safety / Fabrication. Class A kill-switch + Classes B-E judge.
        dim_scores[5], kill_active, kill_reasons = self._dim5_score(
            therasense, hallucination_taxonomy
        )

        # Dim 6 / 7 — vendor metadata, not per-draft.
        dim_scores[6] = DimensionScore(
            dimension=6,
            weight=DIMENSION_WEIGHTS[6],
            score=None,
            note=DEFERRED_DIMENSIONS[6],
        )
        dim_scores[7] = DimensionScore(
            dimension=7,
            weight=DIMENSION_WEIGHTS[7],
            score=None,
            note=DEFERRED_DIMENSIONS[7],
        )

        # Aggregate.
        scored_weight = sum(d.weight for d in dim_scores.values() if d.score is not None)
        total_weight = sum(d.weight for d in dim_scores.values())
        composite_raw = sum(
            d.weight * (d.score or 0.0)
            for d in dim_scores.values()
            if d.score is not None
        )
        coverage = scored_weight / total_weight if total_weight > 0 else 0.0
        extrapolated = composite_raw / scored_weight if scored_weight > 0 else 0.0

        if kill_active:
            # Therasense — instant fail. Hard floor on the composite, regardless of
            # any other dimension. METHODOLOGY.md Dim 5 sub-criteria.
            composite_raw = 0.0
            extrapolated = 0.0
            notes.append("Therasense kill-switch active — composite floored at 0.0")

        for dim_id, reason in DEFERRED_DIMENSIONS.items():
            notes.append(f"Dim {dim_id} not scored at v1.0: {reason}")

        return CompositeScore(
            invention_id=invention_id,
            model_name=model_name,
            composite=composite_raw,
            coverage=coverage,
            extrapolated_composite=extrapolated,
            dimension_scores=dim_scores,
            kill_switch_active=kill_active,
            kill_switch_reasons=kill_reasons,
            notes=notes,
        )

    # --------------------------------------------------------------------- dims

    def _dim1_score(self, metrics: dict | None, notes: list[str]) -> DimensionScore:
        if not metrics:
            return DimensionScore(
                dimension=1,
                weight=DIMENSION_WEIGHTS[1],
                score=None,
                note="No Layer 1 metrics supplied; Dim 1 needs panel for full scoring.",
            )
        # Coarse structural signal: same five checks as DeterministicEvaluator.
        checks = [
            metrics.get("has_abstract", False),
            metrics.get("has_claims", False),
            metrics.get("has_specification", False),
            metrics.get("abstract_within_150w", False),
            (metrics.get("claims") or {}).get("independent", 0) >= 1,
        ]
        score = sum(1 for c in checks if c) / len(checks)
        notes.append("Dim 1 Layer-1 partial signal only — strategic claim quality requires Track B panel.")
        return DimensionScore(
            dimension=1,
            weight=DIMENSION_WEIGHTS[1],
            score=score,
            sources=["layer_1_structural"],
            note="Partial — auto-metrics only. Track B panel needed for strategic claim assessment.",
        )

    def _dim2_score(
        self,
        section_112_us: Section112USEvaluation | None,
        jurisdictional: JurisdictionalEvaluation | None,
        notes: list[str],
    ) -> DimensionScore:
        us_score: float | None = None
        non_us_score: float | None = None
        sources: list[str] = []

        if section_112_us is not None and section_112_us.primary.succeeded:
            us_score = section_112_us.merged_score
            sources.append("layer_2_section_112_us")
        if jurisdictional is not None and jurisdictional.all_succeeded:
            non_us_score = jurisdictional.merged_score
            sources.append("layer_4_jurisdictional")

        if us_score is None and non_us_score is None:
            return DimensionScore(
                dimension=2,
                weight=DIMENSION_WEIGHTS[2],
                score=None,
                note="Neither Layer 2 nor Layer 4 ran successfully.",
            )
        if us_score is not None and non_us_score is not None:
            merged = DIM2_US_WEIGHT * us_score + DIM2_NON_US_WEIGHT * non_us_score
            note = ""
        elif us_score is not None:
            merged = us_score
            note = "Layer 4 jurisdictional did not run — Dim 2 scored on US §112 only."
            notes.append(note)
        else:
            assert non_us_score is not None  # for the type checker
            merged = non_us_score
            note = "Layer 2 §112 US did not run — Dim 2 scored on EP/CN/JP only."
            notes.append(note)
        return DimensionScore(
            dimension=2,
            weight=DIMENSION_WEIGHTS[2],
            score=merged,
            sources=sources,
            note=note,
        )

    def _dim5_score(
        self,
        therasense: TheresenseResult | None,
        taxonomy: HallucinationTaxonomyResult | None,
    ) -> tuple[DimensionScore, bool, list[str]]:
        kill_active = False
        kill_reasons: list[str] = []
        sources: list[str] = []

        # Class A — Therasense.
        class_a_score: float | None = None
        if therasense is not None:
            sources.append("layer_5a_therasense")
            if therasense.triggered:
                kill_active = True
                class_a_score = 0.0
                for cite in therasense.fabricated_citations:
                    kill_reasons.append(f"Class A — fabricated citation: {cite}")
            elif therasense.cited_count == 0:
                # No citations to verify → A-class signal is moot; treat as full credit on the A axis.
                class_a_score = 1.0
            elif therasense.all_verified:
                class_a_score = 1.0
            else:
                # Some citations unverified → partial credit (we can't claim no fabrication).
                verified_ratio = (
                    therasense.verified_exists / therasense.cited_count
                    if therasense.cited_count > 0
                    else 0.0
                )
                class_a_score = max(0.5, verified_ratio)

        # Classes B-E — taxonomy judge.
        bce_score: float | None = None
        if taxonomy is not None and taxonomy.judge_result.succeeded:
            sources.append("layer_5b_hallucination_taxonomy")
            bce_score = taxonomy.score

        if class_a_score is None and bce_score is None:
            return (
                DimensionScore(
                    dimension=5,
                    weight=DIMENSION_WEIGHTS[5],
                    score=None,
                    note="Neither Layer 5A nor Layer 5B ran.",
                ),
                kill_active,
                kill_reasons,
            )

        if kill_active:
            return (
                DimensionScore(
                    dimension=5,
                    weight=DIMENSION_WEIGHTS[5],
                    score=0.0,
                    sources=sources,
                    note="Therasense kill-switch — instant fail on Dim 5.",
                ),
                kill_active,
                kill_reasons,
            )

        if class_a_score is not None and bce_score is not None:
            merged = DIM5_CLASS_A_WEIGHT * class_a_score + DIM5_CLASSES_BE_WEIGHT * bce_score
            note = ""
        elif class_a_score is not None:
            merged = class_a_score
            note = "Layer 5B did not run — Dim 5 scored on Class A only."
        else:
            merged = bce_score or 0.0
            note = "Layer 5A did not run — Dim 5 scored on Classes B-E only."

        return (
            DimensionScore(
                dimension=5,
                weight=DIMENSION_WEIGHTS[5],
                score=merged,
                sources=sources,
                note=note,
            ),
            kill_active,
            kill_reasons,
        )

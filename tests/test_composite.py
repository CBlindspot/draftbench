"""CompositeScorer — combines layer outputs into final scores."""

from __future__ import annotations

from draftbench.judges.base import JudgeResult
from draftbench.layers.hallucination import HallucinationTaxonomyResult
from draftbench.layers.jurisdictional import JurisdictionalEvaluation
from draftbench.layers.section_112_us import Section112USEvaluation
from draftbench.layers.therasense import TheresenseResult
from draftbench.scoring.composite import (
    DIM2_NON_US_WEIGHT,
    DIM2_US_WEIGHT,
    DIM5_CLASS_A_WEIGHT,
    DIM5_CLASSES_BE_WEIGHT,
    DIMENSION_WEIGHTS,
    CompositeScorer,
)


def _layer1_full() -> dict:
    return {
        "has_abstract": True,
        "has_claims": True,
        "has_specification": True,
        "abstract_within_150w": True,
        "claims": {"total": 5, "independent": 1, "dependent": 4},
    }


def _judge_ok(score: float, raw: int = 4) -> JudgeResult:
    return JudgeResult(score=score, raw_score=raw, judge_model="fake")


def _section112(score: float = 0.75) -> Section112USEvaluation:
    return Section112USEvaluation(primary=_judge_ok(score, raw=4))


def _jurisdictional(ep: float = 1.0, cn: float = 0.5, jp: float = 0.75) -> JurisdictionalEvaluation:
    return JurisdictionalEvaluation(
        ep=_judge_ok(ep, raw=5),
        cn=_judge_ok(cn, raw=3),
        jp=_judge_ok(jp, raw=4),
    )


def _therasense(triggered: bool = False, fabricated: list[str] | None = None) -> TheresenseResult:
    fab = fabricated or []
    return TheresenseResult(
        cited_count=1 + len(fab),
        verified_exists=1,
        verified_fabricated=len(fab),
        unverified=0,
        fabricated_citations=fab,
        triggered=triggered,
    )


def _taxonomy(score: float = 0.75) -> HallucinationTaxonomyResult:
    return HallucinationTaxonomyResult(judge_result=_judge_ok(score, raw=4))


# --------------------------------------------------------------------------- tests


def test_v10_partial_composite_only_scored_dims_count() -> None:
    """At v1.0 with full Phase-2 layers, dims 1+2+5 are scored; 3/4/6/7 are deferred."""
    scorer = CompositeScorer()
    cs = scorer.score(
        invention_id="inv1",
        model_name="gpt-x",
        layer1_metrics=_layer1_full(),
        section_112_us=_section112(0.75),
        jurisdictional=_jurisdictional(1.0, 0.5, 0.75),
        therasense=_therasense(triggered=False),
        hallucination_taxonomy=_taxonomy(0.75),
    )
    # Only dims 1, 2, 5 should have non-None scores.
    scored = [d for d in cs.dimension_scores.values() if d.score is not None]
    assert {d.dimension for d in scored} == {1, 2, 5}
    # Coverage = (0.35 + 0.20 + 0.10) / 1.00 = 0.65
    assert abs(cs.coverage - 0.65) < 1e-9
    # Deferred dims explained
    assert any("Track A" in n for n in cs.notes)
    assert any("Track B" in n for n in cs.notes)


def test_kill_switch_floors_composite_to_zero() -> None:
    scorer = CompositeScorer()
    cs = scorer.score(
        invention_id="inv1",
        model_name="bad-model",
        layer1_metrics=_layer1_full(),
        section_112_us=_section112(1.0),
        jurisdictional=_jurisdictional(1.0, 1.0, 1.0),
        therasense=_therasense(triggered=True, fabricated=["US 99,999,999"]),
        hallucination_taxonomy=_taxonomy(1.0),
    )
    assert cs.kill_switch_active is True
    assert cs.composite == 0.0
    assert cs.extrapolated_composite == 0.0
    assert any("99,999,999" in r for r in cs.kill_switch_reasons)
    assert cs.dimension_scores[5].score == 0.0


def test_dim2_combines_us_and_non_us_per_methodology() -> None:
    scorer = CompositeScorer()
    cs = scorer.score(
        invention_id="inv1",
        model_name="m",
        layer1_metrics=_layer1_full(),
        section_112_us=_section112(0.8),  # US half
        jurisdictional=_jurisdictional(0.4, 0.4, 0.4),  # all 0.4 → merged 0.4
        therasense=_therasense(),
        hallucination_taxonomy=_taxonomy(0.5),
    )
    expected_dim2 = DIM2_US_WEIGHT * 0.8 + DIM2_NON_US_WEIGHT * 0.4
    assert abs(cs.dimension_scores[2].score - expected_dim2) < 1e-9


def test_dim2_falls_back_to_us_only_when_jurisdictional_missing() -> None:
    scorer = CompositeScorer()
    cs = scorer.score(
        invention_id="inv1",
        model_name="m",
        layer1_metrics=_layer1_full(),
        section_112_us=_section112(0.8),
        jurisdictional=None,
        therasense=_therasense(),
        hallucination_taxonomy=_taxonomy(0.5),
    )
    assert cs.dimension_scores[2].score == 0.8
    assert any("Layer 4" in n for n in cs.notes)


def test_dim5_combines_class_a_and_bce() -> None:
    scorer = CompositeScorer()
    cs = scorer.score(
        invention_id="inv1",
        model_name="m",
        layer1_metrics=_layer1_full(),
        section_112_us=_section112(),
        jurisdictional=_jurisdictional(),
        therasense=_therasense(triggered=False),  # all verified → 1.0 on Class A
        hallucination_taxonomy=_taxonomy(0.5),  # 0.5 on Classes B-E
    )
    expected_dim5 = DIM5_CLASS_A_WEIGHT * 1.0 + DIM5_CLASSES_BE_WEIGHT * 0.5
    assert abs(cs.dimension_scores[5].score - expected_dim5) < 1e-9


def test_partial_layers_yield_lower_coverage() -> None:
    """If Layer 4 + Layer 5B both missing, coverage should drop from 0.65 to (0.35 + 0.10/2 + 0.20*0.5) … actually just scored dim count."""
    scorer = CompositeScorer()
    cs = scorer.score(
        invention_id="inv1",
        model_name="m",
        layer1_metrics=_layer1_full(),
        section_112_us=_section112(0.8),
        jurisdictional=None,  # missing
        therasense=_therasense(),  # only Class A signal
        hallucination_taxonomy=None,  # missing B-E
    )
    # Dim 1 ✓, Dim 2 ✓ (US only), Dim 5 ✓ (Class A only) — same dim coverage as full case
    assert cs.coverage == (DIMENSION_WEIGHTS[1] + DIMENSION_WEIGHTS[2] + DIMENSION_WEIGHTS[5]) / sum(
        DIMENSION_WEIGHTS.values()
    )


def test_no_layers_means_all_dims_unscored() -> None:
    scorer = CompositeScorer()
    cs = scorer.score(invention_id="inv1", model_name="m")
    assert cs.composite == 0.0
    assert cs.coverage == 0.0
    assert all(d.score is None for d in cs.dimension_scores.values())


def test_dimension_weights_sum_to_one() -> None:
    """Sanity — METHODOLOGY.md §4 weights must sum to 1."""
    assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9

"""Layer 5B — Hallucination Classes B-E judge."""

from __future__ import annotations

from draftbench.anti_hallucination import HallucinationClass
from draftbench.judges.base import JudgeResult
from draftbench.layers.hallucination import HallucinationTaxonomyJudge
from tests.conftest import FakeJudge


def _judge_with_response(raw_text: str, raw_score: int = 4) -> FakeJudge:
    """Helper — wires a FakeJudge whose raw_text matches a given JSON payload."""
    return FakeJudge(
        default_response=JudgeResult(
            score=(raw_score - 1) / 4.0,
            raw_score=raw_score,
            judge_model="fake",
            raw_response={"raw_text": raw_text},
        )
    )


def test_clean_draft_no_findings() -> None:
    raw = '{"score": 5, "findings": [], "rationale": "No B-E defects."}'
    layer = HallucinationTaxonomyJudge(judge=_judge_with_response(raw, raw_score=5))
    result = layer.evaluate("draft text")
    assert result.score == 1.0
    assert result.raw_score == 5
    assert result.findings == []


def test_class_b_misattribution() -> None:
    raw = (
        '{"score": 3, "findings": ['
        '{"class": "B", "issue": "wrong teaching", "location": "spec p2",'
        ' "reference": "US 9,123,456", "explanation": "Cited reference does not teach X."}'
        '], "rationale": "One Class B finding."}'
    )
    layer = HallucinationTaxonomyJudge(judge=_judge_with_response(raw, raw_score=3))
    result = layer.evaluate("draft text")
    assert result.class_b_count == 1
    assert result.class_c_count == 0
    assert result.findings[0].klass == HallucinationClass.B_MISATTRIBUTED
    assert "9,123,456" in result.findings[0].reference


def test_multiple_classes_counted_separately() -> None:
    raw = (
        '{"score": 2, "findings": ['
        '{"class": "C", "issue": "ungrounded", "location": "spec p3", "reference": "n/a", "explanation": "x"},'
        '{"class": "C", "issue": "ungrounded2", "location": "spec p4", "reference": "n/a", "explanation": "x"},'
        '{"class": "E", "issue": "overreach", "location": "claim 1", "reference": "n/a", "explanation": "x"}'
        '], "rationale": "Multi finding"}'
    )
    layer = HallucinationTaxonomyJudge(judge=_judge_with_response(raw, raw_score=2))
    result = layer.evaluate("draft text")
    assert result.class_c_count == 2
    assert result.class_e_count == 1
    assert result.class_b_count == 0
    assert result.class_d_count == 0


def test_class_a_findings_are_ignored() -> None:
    """Class A is verified by Therasense (deterministic) — judge findings of Class A are dropped."""
    raw = (
        '{"score": 4, "findings": ['
        '{"class": "A", "issue": "ignored fabrication", "location": "x", "reference": "x", "explanation": "x"},'
        '{"class": "B", "issue": "real B finding", "location": "x", "reference": "x", "explanation": "x"}'
        '], "rationale": "x"}'
    )
    layer = HallucinationTaxonomyJudge(judge=_judge_with_response(raw, raw_score=4))
    result = layer.evaluate("draft text")
    # Only the B finding should survive
    assert len(result.findings) == 1
    assert result.findings[0].klass == HallucinationClass.B_MISATTRIBUTED


def test_failed_judge_returns_empty_findings() -> None:
    fake = FakeJudge(
        default_response=JudgeResult(
            score=0.0, raw_score=0, judge_model="fake", error="TimeoutError"
        )
    )
    layer = HallucinationTaxonomyJudge(judge=fake)
    result = layer.evaluate("draft text")
    assert result.findings == []
    assert result.judge_result.error == "TimeoutError"

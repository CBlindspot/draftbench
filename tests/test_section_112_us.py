"""Layer 2 §112 US judge — orchestration via a fake judge."""

from __future__ import annotations

from draftbench.judges.base import JudgeFinding, JudgeResult
from draftbench.layers.section_112_us import Section112USJudge
from tests.conftest import FakeJudge

SAMPLE_DRAFT = """=== ABSTRACT ===
A toroidal cable clamp.

=== CLAIMS ===
1. A clamp comprising a toroidal body, an elastomer insert, and a keyed boss.

=== SPECIFICATION ===
Detailed Description. The clamp uses dual-durometer silicone.
"""


def test_section_112_us_runs_judge_with_rubric() -> None:
    fake = FakeJudge()
    layer = Section112USJudge(judge=fake)
    eval_result = layer.evaluate(SAMPLE_DRAFT)

    assert len(fake.calls) == 1
    call = fake.calls[0]
    # System prompt locked to §112 specifics
    assert "§112" in call["system"]
    assert "JSON" in call["system"]
    # User prompt embeds the rubric + the draft
    assert "Specification Quality" in call["user"]
    assert "toroidal cable clamp" in call["user"]
    # Result wraps the primary judge output
    assert eval_result.primary.raw_score == 4
    assert eval_result.secondary is None
    assert eval_result.score_variance is None


def test_cross_family_validation_averages_scores() -> None:
    primary = FakeJudge(
        default_response=JudgeResult(
            score=0.75, raw_score=4, judge_model="primary", rationale="ok"
        )
    )
    secondary = FakeJudge(
        default_response=JudgeResult(
            score=0.50, raw_score=3, judge_model="secondary", rationale="meh"
        )
    )
    layer = Section112USJudge(judge=primary)
    eval_result = layer.evaluate(SAMPLE_DRAFT, cross_judge=secondary)

    assert eval_result.primary.score == 0.75
    assert eval_result.secondary is not None
    assert eval_result.secondary.score == 0.50
    assert eval_result.merged_score == 0.625
    assert eval_result.score_variance == 0.25


def test_failed_secondary_falls_back_to_primary() -> None:
    primary = FakeJudge(
        default_response=JudgeResult(
            score=0.75, raw_score=4, judge_model="primary", rationale="ok"
        )
    )
    secondary = FakeJudge(
        default_response=JudgeResult(
            score=0.0, raw_score=0, judge_model="secondary", error="TimeoutError: x"
        )
    )
    layer = Section112USJudge(judge=primary)
    eval_result = layer.evaluate(SAMPLE_DRAFT, cross_judge=secondary)

    # secondary errored → merged_score uses primary only
    assert eval_result.merged_score == 0.75
    # variance is undefined when secondary failed
    assert eval_result.score_variance is None


def test_findings_propagate_into_evaluation() -> None:
    fake = FakeJudge(
        default_response=JudgeResult(
            score=0.25,
            raw_score=2,
            findings=[
                JudgeFinding(
                    issue="missing enablement",
                    severity="critical",
                    location="Detailed Description, line 1",
                    explanation="No working example for dual-durometer ratio.",
                )
            ],
            rationale="§112(a) failure on enablement.",
            judge_model="fake",
        )
    )
    layer = Section112USJudge(judge=fake)
    eval_result = layer.evaluate(SAMPLE_DRAFT)

    assert len(eval_result.primary.findings) == 1
    assert eval_result.primary.findings[0].severity == "critical"
    assert "enablement" in eval_result.primary.findings[0].issue

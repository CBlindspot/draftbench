"""Layer 4 — Jurisdictional EP/CN/JP judge."""

from __future__ import annotations

from draftbench.judges.base import JudgeResult
from draftbench.layers.jurisdictional import WEIGHTS, JurisdictionalJudge
from tests.conftest import FakeJudge


def _judge_with_response(raw_text: str) -> FakeJudge:
    return FakeJudge(
        default_response=JudgeResult(
            score=0.5,  # the parent score is unused — _split_verdicts re-derives per-jurisdiction
            raw_score=3,
            judge_model="fake",
            raw_response={"raw_text": raw_text, "id": "test-call"},
        )
    )


def test_three_jurisdictions_extracted() -> None:
    raw = (
        '{"ep": {"score": 4, "findings": [], "rationale": "EP ok"},'
        ' "cn": {"score": 3, "findings": [], "rationale": "CN partial"},'
        ' "jp": {"score": 5, "findings": [], "rationale": "JP excellent"}}'
    )
    layer = JurisdictionalJudge(judge=_judge_with_response(raw))
    result = layer.evaluate("draft")
    assert result.ep.raw_score == 4
    assert result.cn.raw_score == 3
    assert result.jp.raw_score == 5
    assert result.all_succeeded


def test_merged_score_weighted_correctly() -> None:
    raw = (
        '{"ep": {"score": 5, "findings": [], "rationale": "x"},'
        ' "cn": {"score": 1, "findings": [], "rationale": "x"},'
        ' "jp": {"score": 3, "findings": [], "rationale": "x"}}'
    )
    layer = JurisdictionalJudge(judge=_judge_with_response(raw))
    result = layer.evaluate("draft")
    # ep=1.0, cn=0.0, jp=0.5 → 0.4*1.0 + 0.3*0.0 + 0.3*0.5 = 0.55
    expected = WEIGHTS["ep"] * 1.0 + WEIGHTS["cn"] * 0.0 + WEIGHTS["jp"] * 0.5
    assert abs(result.merged_score - expected) < 1e-9


def test_findings_propagate_per_jurisdiction() -> None:
    raw = (
        '{"ep": {"score": 3, "findings": ['
        '{"issue": "Art 84 ambiguity", "severity": "major", "location": "claim 2", "explanation": "x"}'
        '], "rationale": "EP partial"},'
        ' "cn": {"score": 4, "findings": [], "rationale": "CN ok"},'
        ' "jp": {"score": 4, "findings": [], "rationale": "JP ok"}}'
    )
    layer = JurisdictionalJudge(judge=_judge_with_response(raw))
    result = layer.evaluate("draft")
    assert len(result.ep.findings) == 1
    assert result.ep.findings[0].severity == "major"
    assert "Art 84" in result.ep.findings[0].issue


def test_malformed_response_returns_failed_subjudges() -> None:
    raw = "not even json"
    layer = JurisdictionalJudge(judge=_judge_with_response(raw))
    result = layer.evaluate("draft")
    assert result.ep.error is not None
    assert result.cn.error is not None
    assert result.jp.error is not None
    assert not result.all_succeeded


def test_missing_jurisdiction_block_marks_that_one_failed() -> None:
    raw = (
        '{"ep": {"score": 4, "findings": [], "rationale": "ok"},'
        ' "cn": {"score": 3, "findings": [], "rationale": "ok"}}'
        # JP block missing
    )
    layer = JurisdictionalJudge(judge=_judge_with_response(raw))
    result = layer.evaluate("draft")
    assert result.ep.succeeded
    assert result.cn.succeeded
    assert result.jp.error is not None


def test_failed_parent_judge_propagates() -> None:
    failed = FakeJudge(
        default_response=JudgeResult(
            score=0.0, raw_score=0, judge_model="fake", error="HTTP 500"
        )
    )
    layer = JurisdictionalJudge(judge=failed)
    result = layer.evaluate("draft")
    assert all(not r.succeeded for r in (result.ep, result.cn, result.jp))

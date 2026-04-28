"""HTMLReportGenerator — basic structural checks."""

from __future__ import annotations

from draftbench.scoring.composite import (
    DIMENSION_WEIGHTS,
    CompositeScore,
    DimensionScore,
)
from draftbench.scoring.report import HTMLReportGenerator


def _make_score(
    invention_id: str,
    model_name: str,
    composite: float,
    kill: bool = False,
) -> CompositeScore:
    dim_scores = {
        1: DimensionScore(1, DIMENSION_WEIGHTS[1], composite, sources=["layer_1_structural"]),
        2: DimensionScore(2, DIMENSION_WEIGHTS[2], composite, sources=["layer_2_section_112_us"]),
        3: DimensionScore(3, DIMENSION_WEIGHTS[3], None, note="deferred"),
        4: DimensionScore(4, DIMENSION_WEIGHTS[4], None, note="deferred"),
        5: DimensionScore(5, DIMENSION_WEIGHTS[5], 0.0 if kill else composite),
        6: DimensionScore(6, DIMENSION_WEIGHTS[6], None, note="vendor"),
        7: DimensionScore(7, DIMENSION_WEIGHTS[7], None, note="vendor"),
    }
    return CompositeScore(
        invention_id=invention_id,
        model_name=model_name,
        composite=0.0 if kill else composite,
        coverage=0.65,
        extrapolated_composite=0.0 if kill else composite,
        dimension_scores=dim_scores,
        kill_switch_active=kill,
        kill_switch_reasons=(["Class A — fabricated citation: US 99,999,999"] if kill else []),
    )


def test_report_renders_minimum_html() -> None:
    scores = [_make_score("inv1", "claude-opus", 0.8)]
    html = HTMLReportGenerator().render(scores, run_metadata={"run_id": "test_run"})
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html
    assert "DraftBench Report" in html


def test_report_includes_run_id_and_methodology_version() -> None:
    scores = [_make_score("inv1", "model-a", 0.7)]
    html = HTMLReportGenerator().render(
        scores, run_metadata={"run_id": "run_20260428-123456", "started_at": "2026-04-28T12:34:56+00:00"}
    )
    assert "run_20260428-123456" in html
    assert "v1.0-draft" in html


def test_report_lists_all_models_in_leaderboard() -> None:
    scores = [
        _make_score("inv1", "claude-opus", 0.85),
        _make_score("inv1", "gpt-5", 0.72),
        _make_score("inv1", "llama-3.3", 0.51),
    ]
    html = HTMLReportGenerator().render(scores)
    assert "claude-opus" in html
    assert "gpt-5" in html
    assert "llama-3.3" in html


def test_report_sorts_leaderboard_by_composite_descending() -> None:
    """Best composite must appear before lower ones in the rendered HTML."""
    scores = [
        _make_score("inv1", "low-model", 0.3),
        _make_score("inv1", "high-model", 0.9),
        _make_score("inv1", "mid-model", 0.6),
    ]
    html = HTMLReportGenerator().render(scores)
    high_pos = html.find("high-model")
    mid_pos = html.find("mid-model")
    low_pos = html.find("low-model")
    assert 0 < high_pos < mid_pos < low_pos


def test_report_flags_kill_switch_findings() -> None:
    scores = [
        _make_score("inv1", "fabricator", 0.9, kill=True),
        _make_score("inv1", "honest", 0.8, kill=False),
    ]
    html = HTMLReportGenerator().render(scores)
    assert "KILL-SWITCH" in html
    assert "99,999,999" in html
    assert "fabricator" in html


def test_report_omits_pareto_when_no_costs() -> None:
    scores = [_make_score("inv1", "m", 0.7)]
    html = HTMLReportGenerator().render(scores, drafts=[])
    assert "Pareto plot omitted" in html or "No cost data" in html


def test_report_includes_pareto_when_costs_present() -> None:
    scores = [_make_score("inv1", "m1", 0.7), _make_score("inv1", "m2", 0.5)]
    drafts = [
        {"model_name": "m1", "invention_id": "inv1", "cost_usd": 0.05},
        {"model_name": "m2", "invention_id": "inv1", "cost_usd": 0.02},
    ]
    html = HTMLReportGenerator().render(scores, drafts=drafts)
    assert "paretoChart" in html
    assert "chart.js" in html


def test_report_includes_v10_caveat() -> None:
    scores = [_make_score("inv1", "m", 0.7)]
    html = HTMLReportGenerator().render(scores)
    assert "v1.0-draft" in html
    assert "Track A" in html
    assert "Track B" in html


def test_report_aggregates_repeats_per_model() -> None:
    """Multiple repeats of the same model on the same invention → one leaderboard row."""
    scores = [
        _make_score("inv1", "m1", 0.6),
        _make_score("inv1", "m1", 0.8),  # repeat
        _make_score("inv1", "m2", 0.5),
    ]
    html = HTMLReportGenerator().render(scores)
    # m1 should appear once in the leaderboard table (each model once)
    # The rendered HTML may contain the model name multiple times across
    # leaderboard + dimension table, but the count should be consistent for both models.
    m1_count = html.count("m1")
    m2_count = html.count("m2")
    assert m1_count == m2_count  # same number of mentions = one row each in both tables

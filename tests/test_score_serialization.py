"""Round-trip serialization for CompositeScore through the score → report pipeline.

`draftbench score` writes scored results as JSON; `draftbench report` reads
them. The conversion goes through `_score_to_dict` / `_dict_to_score` helpers
in `draftbench/__main__.py`. JSON does not preserve integer dict keys, so
without the `int(k)` coercion in `_dict_to_score`, dimension_scores would
deserialize incorrectly. This test pins the round-trip contract.
"""

from __future__ import annotations

import json

from draftbench.__main__ import _dict_to_score, _score_to_dict
from draftbench.scoring.composite import (
    DIMENSION_WEIGHTS,
    CompositeScore,
    DimensionScore,
)


def _sample_score(kill: bool = False) -> CompositeScore:
    return CompositeScore(
        invention_id="public_widget_clamp",
        model_name="claude-opus-4.7",
        composite=0.0 if kill else 0.78,
        coverage=0.65,
        extrapolated_composite=0.0 if kill else 1.20,
        dimension_scores={
            1: DimensionScore(
                dimension=1,
                weight=DIMENSION_WEIGHTS[1],
                score=0.85,
                sources=["layer_1_structural"],
                note="partial",
            ),
            2: DimensionScore(2, DIMENSION_WEIGHTS[2], 0.75, ["layer_2_section_112_us"], ""),
            3: DimensionScore(3, DIMENSION_WEIGHTS[3], None, [], "deferred to v1.1"),
            4: DimensionScore(4, DIMENSION_WEIGHTS[4], None, [], "deferred to v1.1"),
            5: DimensionScore(5, DIMENSION_WEIGHTS[5], 0.0 if kill else 0.7, [], ""),
            6: DimensionScore(6, DIMENSION_WEIGHTS[6], None, [], "vendor metadata"),
            7: DimensionScore(7, DIMENSION_WEIGHTS[7], None, [], "vendor metadata"),
        },
        kill_switch_active=kill,
        kill_switch_reasons=(["Class A — fabricated US 99,999,999"] if kill else []),
        notes=["Dim 1 Layer-1 partial signal only", "Dim 3 deferred to v1.1"],
    )


def test_round_trip_preserves_all_fields() -> None:
    original = _sample_score(kill=False)
    serialized = _score_to_dict(original)
    # JSON-encode + decode to mimic the exact path used by score → report
    json_str = json.dumps(serialized)
    deserialized = _dict_to_score(json.loads(json_str))

    assert deserialized.invention_id == original.invention_id
    assert deserialized.model_name == original.model_name
    assert abs(deserialized.composite - original.composite) < 1e-9
    assert abs(deserialized.coverage - original.coverage) < 1e-9
    assert deserialized.kill_switch_active == original.kill_switch_active
    assert deserialized.notes == original.notes


def test_round_trip_preserves_dimension_scores_with_int_keys() -> None:
    """JSON coerces int keys to strings; deserialization must coerce back."""
    original = _sample_score()
    json_str = json.dumps(_score_to_dict(original))
    # Verify the JSON uses string keys (sanity check)
    raw = json.loads(json_str)
    assert "1" in raw["dimension_scores"]
    assert 1 not in raw["dimension_scores"]  # JSON has string keys

    deserialized = _dict_to_score(raw)
    # After deserialization, keys should be int again
    assert 1 in deserialized.dimension_scores
    assert isinstance(list(deserialized.dimension_scores.keys())[0], int)


def test_round_trip_preserves_kill_switch_state() -> None:
    original = _sample_score(kill=True)
    json_str = json.dumps(_score_to_dict(original))
    deserialized = _dict_to_score(json.loads(json_str))

    assert deserialized.kill_switch_active is True
    assert deserialized.kill_switch_reasons == original.kill_switch_reasons
    assert deserialized.dimension_scores[5].score == 0.0
    assert deserialized.composite == 0.0


def test_round_trip_preserves_none_dimensions() -> None:
    """Deferred dimensions have score=None — must round-trip as None, not 0.0."""
    original = _sample_score()
    deserialized = _dict_to_score(json.loads(json.dumps(_score_to_dict(original))))
    for deferred in (3, 4, 6, 7):
        assert deserialized.dimension_scores[deferred].score is None


def test_round_trip_preserves_dimension_sources_and_notes() -> None:
    original = _sample_score()
    deserialized = _dict_to_score(json.loads(json.dumps(_score_to_dict(original))))
    assert deserialized.dimension_scores[1].sources == ["layer_1_structural"]
    assert deserialized.dimension_scores[1].note == "partial"
    assert deserialized.dimension_scores[3].note == "deferred to v1.1"

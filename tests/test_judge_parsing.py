"""Robust JSON extraction from LLM judge responses."""

from __future__ import annotations

import pytest

from draftbench.judges.parsing import parse_judge_json


def test_plain_json() -> None:
    text = '{"score": 4, "rationale": "Good draft"}'
    out = parse_judge_json(text)
    assert out["score"] == 4
    assert out["rationale"] == "Good draft"


def test_json_in_code_block() -> None:
    text = '```json\n{"score": 3, "findings": []}\n```'
    out = parse_judge_json(text)
    assert out["score"] == 3
    assert out["findings"] == []


def test_json_in_unfenced_code_block() -> None:
    text = '```\n{"score": 5}\n```'
    out = parse_judge_json(text)
    assert out["score"] == 5


def test_json_with_prose_preamble() -> None:
    text = """Here is my evaluation:

{"score": 2, "rationale": "Several §112 issues"}

Hope this helps."""
    out = parse_judge_json(text)
    assert out["score"] == 2


def test_json_with_nested_braces() -> None:
    text = """Result: {"score": 4, "findings": [{"issue": "x", "explanation": "y"}], "rationale": "ok"}"""
    out = parse_judge_json(text)
    assert out["score"] == 4
    assert len(out["findings"]) == 1
    assert out["findings"][0]["issue"] == "x"


def test_json_with_strings_containing_braces() -> None:
    text = '{"score": 3, "rationale": "The {bracketed} term is fine"}'
    out = parse_judge_json(text)
    assert out["score"] == 3
    assert "{bracketed}" in out["rationale"]


def test_empty_response_raises() -> None:
    with pytest.raises(ValueError, match="Empty"):
        parse_judge_json("")


def test_non_json_response_raises() -> None:
    with pytest.raises(ValueError, match="Could not extract"):
        parse_judge_json("This is just prose, no JSON.")


def test_malformed_braces_raises() -> None:
    with pytest.raises(ValueError):
        parse_judge_json("{not valid json: missing quotes}")

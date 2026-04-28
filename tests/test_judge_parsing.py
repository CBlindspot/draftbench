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


# --------------------------------------------------------- retry behavior


def test_openrouter_judge_retries_on_429(monkeypatch) -> None:
    """A transient 429 must NOT score 0.0 immediately — judge retries up to N times.

    Verifies the fix for the gap where OpenRouterJudge had no retry logic.
    """
    from unittest.mock import MagicMock

    from draftbench.judges import openrouter_judge as orj

    # Sleep is no-op in tests
    monkeypatch.setattr(orj.time, "sleep", lambda _s: None)
    # Avoid the env var check
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    judge = orj.OpenRouterJudge(
        model="test/model", pricing_in=1.0, pricing_out=1.0, max_retries=5
    )

    # First call → 429, second call → success
    class FakeError(Exception):
        def __init__(self, status: int):
            self.status_code = status
            super().__init__(f"HTTP {status}")

    fake_response = MagicMock()
    fake_response.choices = [
        MagicMock(
            message=MagicMock(content='{"score": 4, "rationale": "ok"}'),
            finish_reason="stop",
        )
    ]
    fake_response.usage = MagicMock(prompt_tokens=100, completion_tokens=200)
    fake_response.id = "test-id"
    fake_response.model = "test/model"

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        FakeError(429),  # transient
        fake_response,  # success
    ]
    judge._client = fake_client

    result = judge.judge("system", "user")
    assert result.succeeded is True
    assert result.raw_score == 4
    assert result.raw_response.get("attempts") == 2


def test_openrouter_judge_no_retry_on_4xx_business_error(monkeypatch) -> None:
    """A 401 (auth) or 400 (bad request) should NOT retry — fail-fast on business errors."""
    from unittest.mock import MagicMock

    from draftbench.judges import openrouter_judge as orj

    monkeypatch.setattr(orj.time, "sleep", lambda _s: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    judge = orj.OpenRouterJudge(
        model="test/model", pricing_in=1.0, pricing_out=1.0, max_retries=10
    )

    class FakeError(Exception):
        def __init__(self, status: int):
            self.status_code = status
            super().__init__(f"HTTP {status}")

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = FakeError(401)
    judge._client = fake_client

    result = judge.judge("system", "user")
    assert result.succeeded is False
    assert "401" in (result.error or "")
    # Single call only — no retries on auth error
    assert fake_client.chat.completions.create.call_count == 1


def test_openrouter_judge_persistent_5xx_returns_error(monkeypatch) -> None:
    """If 5xx persists across all retries, return error (not raise)."""
    from unittest.mock import MagicMock

    from draftbench.judges import openrouter_judge as orj

    monkeypatch.setattr(orj.time, "sleep", lambda _s: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    judge = orj.OpenRouterJudge(
        model="test/model", pricing_in=1.0, pricing_out=1.0, max_retries=3
    )

    class FakeError(Exception):
        def __init__(self, status: int):
            self.status_code = status
            super().__init__(f"HTTP {status}")

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = FakeError(503)
    judge._client = fake_client

    result = judge.judge("system", "user")
    assert result.succeeded is False
    assert fake_client.chat.completions.create.call_count == 3  # exhausted all retries

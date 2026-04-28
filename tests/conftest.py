"""Shared pytest fixtures and fakes for the test suite."""

from __future__ import annotations

from typing import Any

from draftbench.judges.base import BaseJudge, JudgeConfig, JudgeFinding, JudgeResult


class FakeJudge(BaseJudge):
    """Test double that returns canned JudgeResults without calling any API.

    Pass `responses` as a list to return them in order on successive calls,
    or `default_response` for a constant response.
    """

    def __init__(
        self,
        responses: list[JudgeResult] | None = None,
        default_response: JudgeResult | None = None,
        judge_model: str = "fake-judge",
    ):
        self._responses = list(responses or [])
        self._default = default_response or JudgeResult(
            score=0.75,
            raw_score=4,
            findings=[JudgeFinding("default issue", "minor", "n/a", "default")],
            rationale="Fake judge default response.",
            judge_model=judge_model,
        )
        self.judge_model = judge_model
        self.calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return True

    def judge(
        self,
        system_prompt: str,
        user_prompt: str,
        config: JudgeConfig | None = None,
    ) -> JudgeResult:
        self.calls.append(
            {"system": system_prompt, "user": user_prompt, "config": config}
        )
        if self._responses:
            return self._responses.pop(0)
        return self._default

"""Layer 2 — §112 US LLM-judge.

Maps to METHODOLOGY.md §6 Layer 2. Scores Dim 2 (Specification Quality, weight
20%) on the US §112 sub-criteria: enablement (a), definiteness (b), and
means-plus-function handling (f).

Cross-family bias control (METHODOLOGY.md §10) is exposed via
`Section112USJudge.cross_family_validate(secondary_judge, ...)`. Default mode
runs a single primary judge; calling code opts in to cross-validation when
needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from draftbench.judges.base import BaseJudge, JudgeConfig, JudgeResult

DIM2_RUBRIC_PATH = (
    Path(__file__).parent.parent.parent / "data" / "rubrics" / "dim2_specification_quality.json"
)

JUDGE_SYSTEM_PROMPT = """You are an expert US patent attorney evaluating §112 conformance of a patent draft.

You score the draft on a 1-5 scale per the rubric provided in the user message. Focus
on:
  - 35 USC §112(a) — enablement (POSITA can make and use the invention)
  - 35 USC §112(a) — written description support for every claim limitation
  - 35 USC §112(b) — definiteness (clear claim terms, no ambiguity)
  - 35 USC §112(f) — means-plus-function structure disclosure when functional language is used

You return STRICT JSON in exactly this shape (no prose outside the JSON object):

{
  "score": <int 1-5>,
  "findings": [
    {
      "issue": "<short label>",
      "severity": "<critical|major|minor>",
      "location": "<section + brief snippet>",
      "explanation": "<one sentence>"
    }
  ],
  "rationale": "<2-3 sentences justifying the score>"
}

Rules:
  - score is an integer 1, 2, 3, 4, or 5 — no halves, no NaN.
  - findings is a list (possibly empty). Each finding identifies one §112 defect.
  - severity = critical for §112(a) enablement failures, major for §112(b) definiteness
    failures or written-description gaps, minor for stylistic ambiguities.
  - location quotes a short snippet so a reviewer can find the issue.
  - rationale ties the score to the specific rubric level (1=Unacceptable through 5=Excellent).
"""


@dataclass
class Section112USEvaluation:
    """Output of a Layer 2 §112 US run on a single draft."""

    primary: JudgeResult
    secondary: JudgeResult | None = None  # cross-family judge, if invoked

    @property
    def merged_score(self) -> float:
        """Average of primary + secondary if both succeeded; else primary only."""
        if self.secondary is not None and self.secondary.succeeded:
            return (self.primary.score + self.secondary.score) / 2
        return self.primary.score

    @property
    def score_variance(self) -> float | None:
        """Absolute difference between primary and secondary scores, in the 0-1 normalized space."""
        if self.secondary is None or not self.secondary.succeeded:
            return None
        return abs(self.primary.score - self.secondary.score)


class Section112USJudge:
    """Layer 2 evaluator. Wraps a `BaseJudge` and the Dim 2 rubric."""

    def __init__(self, judge: BaseJudge, rubric_path: Path | None = None):
        self.judge = judge
        path = rubric_path or DIM2_RUBRIC_PATH
        self.rubric = json.loads(path.read_text(encoding="utf-8"))

    def evaluate(
        self,
        draft_text: str,
        config: JudgeConfig | None = None,
        cross_judge: BaseJudge | None = None,
    ) -> Section112USEvaluation:
        primary = self.judge.judge(
            JUDGE_SYSTEM_PROMPT,
            self._build_user_prompt(draft_text),
            config=config,
        )
        secondary = None
        if cross_judge is not None:
            secondary = cross_judge.judge(
                JUDGE_SYSTEM_PROMPT,
                self._build_user_prompt(draft_text),
                config=config,
            )
        return Section112USEvaluation(primary=primary, secondary=secondary)

    def _build_user_prompt(self, draft_text: str) -> str:
        rubric = self.rubric
        sub_criteria = "\n".join(f"  - {s}" for s in rubric["sub_criteria"])
        levels = "\n".join(
            f"  Score {lvl['score']} ({lvl['label']}): {lvl['criteria']}"
            for lvl in rubric["scoring_levels"]
        )
        return f"""## Rubric — {rubric['dimension']} (weight {rubric['weight']:.0%})

Description: {rubric['description']}

Sub-criteria (US §112 portion):
{sub_criteria}

Scoring levels:
{levels}

## Draft to evaluate

{draft_text}

Score the §112 US conformance of the draft above. Return JSON only — no prose."""

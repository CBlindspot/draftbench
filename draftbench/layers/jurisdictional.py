"""Layer 4 — Jurisdictional EP / CN / JP LLM-judge.

Maps to METHODOLOGY.md §6 Layer 4. Scores the non-US portion of Dim 2
(Specification Quality) by checking the draft against the §112-equivalent
provisions of three jurisdictions:

  EP — EPC Art 83 (sufficient disclosure), Art 84 (clarity / conciseness),
       Art 123(2) (added-matter)
  CN — SIPO Patent Law Art 26.3 (sufficient disclosure) + Art 26.4 (clarity)
  JP — JPO Patent Act Art 36 (enablement + clarity)

A single judge call returns three sub-scores. Composing the per-jurisdiction
scores into a single Layer 4 score uses METHODOLOGY.md §4.1 Dim 2 weights
(US 0.5, EP 0.2, CN 0.15, JP 0.15) — the US 0.5 is supplied by Layer 2; this
module composes only the non-US 0.5 portion: EP=0.4, CN=0.3, JP=0.3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from draftbench.judges.base import BaseJudge, JudgeConfig, JudgeFinding, JudgeResult

DIM2_RUBRIC_PATH = (
    Path(__file__).parent.parent.parent / "data" / "rubrics" / "dim2_specification_quality.json"
)

# Jurisdiction-specific weights for the Layer 4 merged score (the non-US half of Dim 2).
WEIGHTS = {"ep": 0.4, "cn": 0.3, "jp": 0.3}

JUDGE_SYSTEM_PROMPT = """You are an expert international patent attorney evaluating a US-style
patent draft against three non-US jurisdictions. You produce three independent verdicts.

  EP (European Patent Office)  — EPC Art 83 sufficiency, Art 84 clarity / conciseness, Art 123(2) added-matter
  CN (China National IP Admin) — Patent Law Art 26.3 sufficient disclosure, Art 26.4 clarity
  JP (Japan Patent Office)     — Patent Act Art 36 enablement + clarity

Score each jurisdiction 1-5 against the rubric provided in the user message.

You return STRICT JSON (no prose outside the object) in exactly this shape:

{
  "ep": {
    "score": <int 1-5>,
    "findings": [
      {
        "issue": "<short label>",
        "severity": "<critical|major|minor>",
        "location": "<section + snippet>",
        "explanation": "<one sentence>"
      }
    ],
    "rationale": "<2-3 sentences>"
  },
  "cn": { ... same shape ... },
  "jp": { ... same shape ... }
}

Each jurisdiction's rationale should reference the specific Article(s) the score
is keyed to. A score of 5 in any jurisdiction means a competent local agent could
file the draft with no preparatory amendment.
"""


@dataclass
class JurisdictionalEvaluation:
    """Layer 4 output — three independent per-jurisdiction JudgeResults plus their merged score."""

    ep: JudgeResult
    cn: JudgeResult
    jp: JudgeResult

    @property
    def merged_score(self) -> float:
        """Weighted merge per METHODOLOGY.md §4.1 Dim 2 non-US portion (EP 0.4, CN 0.3, JP 0.3)."""
        return (
            WEIGHTS["ep"] * self.ep.score
            + WEIGHTS["cn"] * self.cn.score
            + WEIGHTS["jp"] * self.jp.score
        )

    @property
    def all_succeeded(self) -> bool:
        return self.ep.succeeded and self.cn.succeeded and self.jp.succeeded


class JurisdictionalJudge:
    """Layer 4 evaluator. One judge call → three jurisdiction verdicts."""

    def __init__(self, judge: BaseJudge, rubric_path: Path | None = None):
        self.judge = judge
        path = rubric_path or DIM2_RUBRIC_PATH
        self.rubric = json.loads(path.read_text(encoding="utf-8"))

    def evaluate(
        self,
        draft_text: str,
        config: JudgeConfig | None = None,
    ) -> JurisdictionalEvaluation:
        # Issue one judge call covering all three jurisdictions, then split the
        # combined verdict into three JudgeResult objects so downstream scoring
        # can treat them uniformly.
        primary = self.judge.judge(
            JUDGE_SYSTEM_PROMPT,
            self._build_user_prompt(draft_text),
            config=config,
        )

        if not primary.succeeded:
            failed = JudgeResult(
                score=0.0,
                raw_score=0,
                judge_model=primary.judge_model,
                error=primary.error or "Judge call failed before split",
            )
            return JurisdictionalEvaluation(ep=failed, cn=failed, jp=failed)

        return self._split_verdicts(primary)

    def _build_user_prompt(self, draft_text: str) -> str:
        rubric = self.rubric
        sub_criteria = "\n".join(
            f"  - {s}"
            for s in rubric["sub_criteria"]
            # Filter out the §112 US sub-criteria — Layer 2 handles those.
            if not s.lower().startswith(("§112", "section 112"))
        )
        levels = "\n".join(
            f"  Score {lvl['score']} ({lvl['label']}): {lvl['criteria']}"
            for lvl in rubric["scoring_levels"]
        )
        return f"""## Rubric — {rubric['dimension']} (weight {rubric['weight']:.0%})

Description: {rubric['description']}

Sub-criteria (non-US jurisdictions):
{sub_criteria}

Scoring levels:
{levels}

## Draft to evaluate

{draft_text}

Score the draft against EP, CN, and JP requirements independently. Return JSON only — no prose."""

    def _split_verdicts(self, combined: JudgeResult) -> JurisdictionalEvaluation:
        """Split a combined JSON verdict ({ep, cn, jp}) into three JudgeResult objects."""
        from draftbench.judges.parsing import parse_judge_json

        raw_text = combined.raw_response.get("raw_text", "")
        try:
            data = parse_judge_json(raw_text)
        except ValueError as exc:
            failed = JudgeResult(
                score=0.0,
                raw_score=0,
                judge_model=combined.judge_model,
                error=f"Could not split jurisdictional verdict: {exc}",
            )
            return JurisdictionalEvaluation(ep=failed, cn=failed, jp=failed)

        ep = self._extract(data, "ep", combined)
        cn = self._extract(data, "cn", combined)
        jp = self._extract(data, "jp", combined)
        return JurisdictionalEvaluation(ep=ep, cn=cn, jp=jp)

    @staticmethod
    def _extract(data: dict, key: str, parent: JudgeResult) -> JudgeResult:
        sub = data.get(key)
        if not isinstance(sub, dict):
            return JudgeResult(
                score=0.0,
                raw_score=0,
                judge_model=parent.judge_model,
                error=f"Missing or malformed `{key}` block in judge response",
            )
        raw_score = int(sub.get("score", 0))
        score = max(0.0, min(1.0, (raw_score - 1) / 4.0)) if 1 <= raw_score <= 5 else 0.0
        findings = [
            JudgeFinding(
                issue=str(f.get("issue", "")),
                severity=str(f.get("severity", "minor")).lower(),
                location=str(f.get("location", "n/a")),
                explanation=str(f.get("explanation", "")),
            )
            for f in sub.get("findings", [])
            if isinstance(f, dict)
        ]
        return JudgeResult(
            score=score,
            raw_score=raw_score,
            findings=findings,
            rationale=str(sub.get("rationale", "")).strip(),
            judge_model=f"{parent.judge_model}#{key}",
            cost_usd=parent.cost_usd / 3,  # split the cost across the three sub-verdicts
            latency_ms=parent.latency_ms,
            raw_response={"jurisdiction": key, "parent_id": parent.raw_response.get("id", "")},
        )

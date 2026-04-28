"""Anti-fabrication detection — Therasense kill-switch + 5-class taxonomy.

Maps to METHODOLOGY.md §4.1 Dim 5 sub-criteria:

  Class A — Fabricated prior-art citation (patent number that does not exist)
            → Therasense kill-switch, instant fail
  Class B — Misattributed prior art (citation exists but does not teach what is claimed)
  Class C — Ungrounded technical claim (spec asserts unsupported property)
  Class D — Inconsistent reference (internal contradiction in disclosure)
  Class E — Overreach (claim scope exceeds disclosure support, masked §112(a) defect)

Class A detection is the v1.0 priority — every cited prior-art number is verified
against USPTO Patent Public Search. Classes B-E require LLM-judge passes (Phase 2).

This module ships Class A scaffolding in v1.0; LLM-judge harness for B-E is Phase 2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class HallucinationClass(str, Enum):
    A_FABRICATED_CITATION = "A_fabricated_citation"  # Therasense kill-switch
    B_MISATTRIBUTED = "B_misattributed"
    C_UNGROUNDED_CLAIM = "C_ungrounded_claim"
    D_INCONSISTENT = "D_inconsistent"
    E_OVERREACH = "E_overreach"


# Common patent-number patterns. Loose: catches both "US 9,123,456" and
# "U.S. Pat. No. 9,123,456 B2". Filter to validate against USPTO Patent
# Public Search at verification time.
US_PATENT_RE = re.compile(
    r"\b(?:U\.?\s*S\.?\s*(?:Pat(?:ent)?\.?\s*No\.?)?\s*)?"
    r"(\d{1,2}[,\.\s]?\d{3}[,\.\s]?\d{3})"
    r"(?:\s*[A-Z]\d?)?\b"
)
US_PUBLICATION_RE = re.compile(
    r"\bUS\s*(\d{4})[/-](\d{6,7})\s*A1?\b"
)


@dataclass
class CitedReference:
    raw: str
    normalized: str
    location_in_text: int  # char offset


@dataclass
class HallucinationFinding:
    klass: HallucinationClass
    reference: str
    detail: str
    is_kill_switch: bool = False


@dataclass
class AntiHallucinationResult:
    cited_references: list[CitedReference] = field(default_factory=list)
    findings: list[HallucinationFinding] = field(default_factory=list)
    therasense_triggered: bool = False  # any Class A → True

    @property
    def is_kill_switch_triggered(self) -> bool:
        return self.therasense_triggered


def extract_cited_references(text: str) -> list[CitedReference]:
    """Find every plausible USPTO patent-number / publication-number citation.

    Result is the input set for downstream Class A verification (USPTO Patent
    Public Search lookup, Phase 2). Class A = referenced number does not exist
    in the USPTO record.
    """
    refs: list[CitedReference] = []
    for m in US_PATENT_RE.finditer(text):
        digits = re.sub(r"[^\d]", "", m.group(1))
        if 6 <= len(digits) <= 8:  # plausible US patent number range
            refs.append(
                CitedReference(
                    raw=m.group(0).strip(),
                    normalized=digits,
                    location_in_text=m.start(),
                )
            )
    for m in US_PUBLICATION_RE.finditer(text):
        refs.append(
            CitedReference(
                raw=m.group(0).strip(),
                normalized=f"{m.group(1)}{m.group(2)}",
                location_in_text=m.start(),
            )
        )
    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique: list[CitedReference] = []
    for r in refs:
        if r.normalized not in seen:
            seen.add(r.normalized)
            unique.append(r)
    return unique


def detect_class_a(text: str, valid_patent_numbers: set[str] | None = None) -> AntiHallucinationResult:
    """Class A detection — Therasense kill-switch.

    If `valid_patent_numbers` is provided, every cited reference is checked
    against it; misses become Class A findings. If `valid_patent_numbers` is
    `None`, this returns the cited-reference list without a verdict (intended
    for the verification harness to consume).
    """
    refs = extract_cited_references(text)
    result = AntiHallucinationResult(cited_references=refs)
    if valid_patent_numbers is None:
        return result

    for ref in refs:
        if ref.normalized not in valid_patent_numbers:
            result.findings.append(
                HallucinationFinding(
                    klass=HallucinationClass.A_FABRICATED_CITATION,
                    reference=ref.raw,
                    detail=f"Patent number {ref.normalized} not found in USPTO record.",
                    is_kill_switch=True,
                )
            )
            result.therasense_triggered = True
    return result

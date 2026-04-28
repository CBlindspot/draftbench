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


# Patent-number patterns — STRICT to avoid false-positive Therasense kill-switch
# triggers on phone numbers, serial numbers, or other 7-8-digit sequences. The
# kill-switch is the most consequential signal in the whole harness; a false
# positive (flagging a real, non-fabricated citation as fabricated) is far worse
# than a false negative (missing a fabricated citation) — the latter gets caught
# by Layer 5B Class B/C judging anyway.
#
# We require ONE of two patterns:
#   (1) Patent context prefix — "US 9,123,456", "U.S. Pat. No. 9,123,456 B2"
#   (2) Comma-separated US patent format — "9,123,456" — a syntax that almost
#       never appears outside patent citations.
#
# Phone numbers like "555-123-4567" are excluded by the hyphens (only commas /
# periods / whitespace are accepted as digit-group separators in pattern 2),
# and bare 10-digit strings without separators don't match pattern 1 (no
# context) or pattern 2 (no commas).
US_PATENT_PREFIXED_RE = re.compile(
    r"\b(?:U\.?\s*S\.?\s*(?:Pat(?:ent)?\.?\s*No\.?)?\s*)"  # REQUIRED prefix
    r"(\d{1,2}[,\.\s]?\d{3}[,\.\s]?\d{3})"
    r"(?:\s*[A-Z]\d?)?\b"
)
US_PATENT_BARE_COMMA_RE = re.compile(
    r"(?<![\w\-,])(\d{1,2},\d{3},\d{3})(?![\w\-,])"
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

    Strict-by-design: only matches numbers with explicit patent context (US/Pat
    prefix) or comma-separated format. This means we may miss bare 7-digit
    citations without commas — but Therasense false-positive risk dominates
    false-negative risk (Layer 5B catches missed citations as Class B/C).

    Result is the input set for downstream Class A verification (USPTO Patent
    Public Search lookup). Class A = referenced number does not exist in the
    USPTO record.
    """
    refs: list[CitedReference] = []
    # Pattern 1: with patent context prefix (US, U.S., Pat. No., Patent)
    for m in US_PATENT_PREFIXED_RE.finditer(text):
        digits = re.sub(r"[^\d]", "", m.group(1))
        if 6 <= len(digits) <= 8:
            refs.append(
                CitedReference(
                    raw=m.group(0).strip(),
                    normalized=digits,
                    location_in_text=m.start(),
                )
            )
    # Pattern 2: bare comma-separated US patent number ("9,123,456")
    for m in US_PATENT_BARE_COMMA_RE.finditer(text):
        digits = re.sub(r"[^\d]", "", m.group(1))
        if 6 <= len(digits) <= 8:
            refs.append(
                CitedReference(
                    raw=m.group(1).strip(),
                    normalized=digits,
                    location_in_text=m.start(),
                )
            )
    # Pattern 3: US publication numbers
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

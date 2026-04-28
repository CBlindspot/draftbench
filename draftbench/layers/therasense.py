"""Layer 5A — Therasense kill-switch.

Maps to METHODOLOGY.md §4.1 Dim 5 Class A. For every patent number cited in a
draft, verify it exists in the USPTO record. Fabricated citations (Class A) are
an instant fail on the entire draft — no deduction, no partial credit, hard
floor at score 1.0 on Dim 5 and a kill-switch flag propagating to the composite.

The Therasense doctrine (Therasense v. Becton Dickinson, Fed. Cir. 2011) makes
material misrepresentation of prior art a basis for inequitable conduct findings
that void an entire patent. A drafting tool that fabricates a single prior-art
citation has, in that one act, created the kill-switch event a motivated
litigator will exploit a decade later. There is no acceptable rate of Class A
above zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from draftbench.anti_hallucination import (
    AntiHallucinationResult,
    HallucinationClass,
    HallucinationFinding,
    extract_cited_references,
)
from draftbench.uspto import USPTOClient, VerificationResult


@dataclass
class TheresenseResult:
    """Outcome of running the Therasense kill-switch on a single draft."""

    cited_count: int
    verified_exists: int
    verified_fabricated: int
    unverified: int
    fabricated_citations: list[str] = field(default_factory=list)
    triggered: bool = False
    anti_hallucination: AntiHallucinationResult | None = None

    @property
    def all_verified(self) -> bool:
        return self.unverified == 0

    @property
    def kill_switch_active(self) -> bool:
        return self.triggered


class TheresenseChecker:
    """Wraps the cited-reference extractor and a USPTO client.

    Default behavior on `unverified` (transient API failure, no API key):
    do NOT trigger the kill-switch. Triggering on uncertainty would be a
    false-positive Therasense flag — false-positive rate management is
    explicit in METHODOLOGY.md §11 mitigation 7.
    """

    def __init__(self, uspto: USPTOClient | None = None):
        self.uspto = uspto or USPTOClient()

    def check(self, draft_text: str) -> TheresenseResult:
        refs = extract_cited_references(draft_text)
        anti_hall = AntiHallucinationResult(cited_references=refs)

        verified_exists = 0
        verified_fabricated = 0
        unverified = 0
        fabricated: list[str] = []

        for ref in refs:
            verdict: VerificationResult = self.uspto.verify(ref.normalized)
            if verdict.exists is True:
                verified_exists += 1
            elif verdict.exists is False:
                verified_fabricated += 1
                fabricated.append(ref.raw)
                anti_hall.findings.append(
                    HallucinationFinding(
                        klass=HallucinationClass.A_FABRICATED_CITATION,
                        reference=ref.raw,
                        detail=(
                            f"Patent {ref.normalized} not found in USPTO record "
                            f"(verified via {verdict.source})."
                        ),
                        is_kill_switch=True,
                    )
                )
                anti_hall.therasense_triggered = True
            else:
                unverified += 1

        return TheresenseResult(
            cited_count=len(refs),
            verified_exists=verified_exists,
            verified_fabricated=verified_fabricated,
            unverified=unverified,
            fabricated_citations=fabricated,
            triggered=anti_hall.therasense_triggered,
            anti_hallucination=anti_hall,
        )

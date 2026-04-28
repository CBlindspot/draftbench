"""Layer 5A Therasense kill-switch — orchestration via a fake USPTO client."""

from __future__ import annotations

from draftbench.layers.therasense import TheresenseChecker
from draftbench.uspto import USPTOClient, VerificationResult


class FakeUSPTOClient(USPTOClient):
    """USPTO client that returns canned verdicts from a number→exists mapping."""

    def __init__(self, verdicts: dict[str, bool | None]):
        self._verdicts = verdicts
        self.calls: list[str] = []
        self._memory_cache: dict[str, VerificationResult] = {}

    def verify(self, patent_number: str) -> VerificationResult:
        normalized = "".join(c for c in patent_number if c.isdigit())
        self.calls.append(normalized)
        if normalized in self._verdicts:
            exists = self._verdicts[normalized]
            return VerificationResult(
                patent_number=normalized,
                exists=exists,
                source="patentsview" if exists is not None else "unverified",
                detail="fake",
            )
        return VerificationResult(
            patent_number=normalized,
            exists=None,
            source="unverified",
            detail="fake — no verdict configured",
        )


def test_no_citations_means_no_trigger() -> None:
    fake = FakeUSPTOClient({})
    checker = TheresenseChecker(uspto=fake)
    result = checker.check("Plain text with no patent numbers.")
    assert result.cited_count == 0
    assert result.triggered is False
    assert result.fabricated_citations == []


def test_all_citations_real_no_trigger() -> None:
    fake = FakeUSPTOClient({"9123456": True, "10234567": True})
    checker = TheresenseChecker(uspto=fake)
    result = checker.check("See US 9,123,456 and US 10,234,567 for prior art.")
    assert result.cited_count == 2
    assert result.verified_exists == 2
    assert result.triggered is False


def test_one_fabricated_triggers_kill_switch() -> None:
    fake = FakeUSPTOClient({"9123456": True, "99999999": False})
    checker = TheresenseChecker(uspto=fake)
    result = checker.check(
        "See US 9,123,456 (real) and US 99,999,999 (fabricated)."
    )
    assert result.cited_count == 2
    assert result.verified_exists == 1
    assert result.verified_fabricated == 1
    assert result.triggered is True
    assert "99,999,999" in result.fabricated_citations[0]


def test_unverified_does_not_trigger() -> None:
    """API outage / no key → return None → kill-switch must NOT fire on uncertainty."""
    fake = FakeUSPTOClient({"9123456": None})
    checker = TheresenseChecker(uspto=fake)
    result = checker.check("See US 9,123,456 only.")
    assert result.cited_count == 1
    assert result.unverified == 1
    assert result.triggered is False


def test_anti_hallucination_findings_propagate() -> None:
    fake = FakeUSPTOClient({"99999999": False})
    checker = TheresenseChecker(uspto=fake)
    result = checker.check("See US 99,999,999 (fabricated).")
    assert result.anti_hallucination is not None
    assert len(result.anti_hallucination.findings) == 1
    finding = result.anti_hallucination.findings[0]
    assert finding.is_kill_switch is True
    assert "99999999" in finding.detail or "99,999,999" in finding.detail

"""Class A fabricated-citation extraction."""

from __future__ import annotations

from draftbench.anti_hallucination import (
    HallucinationClass,
    detect_class_a,
    extract_cited_references,
)


def test_extract_us_patent_numbers() -> None:
    text = "See US 9,123,456 and U.S. Pat. No. 10,234,567 B2 for prior art."
    refs = extract_cited_references(text)
    normalized = {r.normalized for r in refs}
    assert "9123456" in normalized
    assert "10234567" in normalized


def test_extract_us_publication_numbers() -> None:
    text = "US 2023/0178923 A1 discloses RAG."
    refs = extract_cited_references(text)
    assert any("20230178923" == r.normalized for r in refs)


def test_dedup_repeated_citations() -> None:
    text = "US 9,123,456 ... and again US 9,123,456 ..."
    refs = extract_cited_references(text)
    assert len(refs) == 1


def test_class_a_kill_switch_triggered() -> None:
    text = "See US 9,123,456 (real) and US 99,999,999 (fabricated)."
    valid = {"9123456"}  # only the first one is real
    result = detect_class_a(text, valid_patent_numbers=valid)
    assert result.therasense_triggered is True
    assert any(
        f.klass == HallucinationClass.A_FABRICATED_CITATION and f.is_kill_switch
        for f in result.findings
    )


def test_class_a_no_findings_when_all_valid() -> None:
    text = "See US 9,123,456 and US 10,234,567."
    valid = {"9123456", "10234567"}
    result = detect_class_a(text, valid_patent_numbers=valid)
    assert result.therasense_triggered is False
    assert result.findings == []


def test_class_a_returns_refs_when_no_validation_set() -> None:
    """When validation set is None, extract refs but don't make a verdict."""
    text = "See US 9,123,456 here."
    result = detect_class_a(text, valid_patent_numbers=None)
    assert len(result.cited_references) == 1
    assert result.therasense_triggered is False
    assert result.findings == []

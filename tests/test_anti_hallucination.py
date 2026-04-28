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


# ------------------------------------------------------------ false-positive guards


def test_phone_number_with_hyphens_not_extracted() -> None:
    """Phone numbers like 555-123-4567 must NOT be flagged as patent citations.

    A false Therasense kill-switch trigger on a footnote phone number would
    fail an entire draft for the wrong reason — the most consequential possible
    false-positive in the whole harness.
    """
    text = "For inquiries call 555-123-4567 or fax 415-555-9876."
    refs = extract_cited_references(text)
    assert refs == []


def test_bare_10_digit_phone_not_extracted() -> None:
    """A 10-digit phone string without separators or patent context must not match."""
    text = "Reach the inventor at 5551234567 during business hours."
    refs = extract_cited_references(text)
    assert refs == []


def test_serial_number_in_text_not_extracted() -> None:
    """A bare 8-digit serial number with no patent context must not match."""
    text = "Device serial 12345678 ships with firmware 2.4.1."
    refs = extract_cited_references(text)
    assert refs == []


def test_bare_comma_formatted_patent_still_caught() -> None:
    """We accept comma-separated patent format even without 'US' prefix."""
    text = "The disclosure builds on 9,123,456 (cable management)."
    refs = extract_cited_references(text)
    assert len(refs) == 1
    assert refs[0].normalized == "9123456"


def test_prefix_required_for_unseparated_digits() -> None:
    """Without commas, we require explicit US/Pat prefix to flag as citation."""
    text_no_prefix = "Reference 9123456 in the paper."
    text_with_prefix = "Reference US 9123456 in the paper."
    assert extract_cited_references(text_no_prefix) == []
    refs = extract_cited_references(text_with_prefix)
    assert len(refs) == 1
    assert refs[0].normalized == "9123456"

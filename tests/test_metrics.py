"""Layer 1 auto-metric extractors."""

from __future__ import annotations

from draftbench.metrics import (
    abstract_word_count,
    count_sections,
    extract_claim_count,
    extract_section,
    summarize_auto_metrics,
)

SAMPLE_DRAFT = """=== ABSTRACT ===
A toroidal cable clamp with a compliant inner lumen and dual-durometer
elastomer insert that self-centers a cable while passively absorbing torsional
load through a keyed mounting boss.

=== CLAIMS ===
1. A cable clamp comprising a toroidal body, an elastomer insert, and a keyed mounting boss.
2. The cable clamp of claim 1, wherein the elastomer insert has Shore 40A inner hardness.
3. The cable clamp of claim 1, wherein the keyed mounting boss permits rotation of plus or minus 15 degrees.
4. A method of mounting a cable, comprising inserting the cable into the toroidal body of the clamp of claim 1.

=== SPECIFICATION ===
Title of the Invention. Cable clamp with passive strain relief.

Cross-Reference to Related Applications. None.

Background. Existing clamps either damage cable insulation or drift under load.

Brief Summary. The disclosed clamp combines a toroidal body with a dual-durometer insert.

Brief Description of Drawings. None.

Detailed Description. In one embodiment, the clamp body is injection-molded polyamide.

Conclusion. The scope of the claims should not be limited to the embodiments above.
"""


def test_count_sections_all_present() -> None:
    found = count_sections(SAMPLE_DRAFT)
    assert found == {"has_abstract": True, "has_claims": True, "has_specification": True}


def test_count_sections_missing() -> None:
    found = count_sections("=== ABSTRACT ===\nshort\n=== CLAIMS ===\n1. claim")
    assert found["has_abstract"] is True
    assert found["has_claims"] is True
    assert found["has_specification"] is False


def test_extract_section_returns_content() -> None:
    abstract = extract_section(SAMPLE_DRAFT, "ABSTRACT")
    assert abstract.startswith("A toroidal cable clamp")
    assert "keyed mounting boss" in abstract


def test_extract_claim_count() -> None:
    claims = extract_claim_count(SAMPLE_DRAFT)
    assert claims["total"] == 4
    assert claims["dependent"] == 3  # claims 2, 3, 4 each "of claim ..."
    assert claims["independent"] == 1


def test_abstract_word_count_within_limit() -> None:
    n = abstract_word_count(SAMPLE_DRAFT)
    assert 0 < n <= 150


def test_summarize_auto_metrics() -> None:
    m = summarize_auto_metrics(SAMPLE_DRAFT)
    assert m["has_abstract"] and m["has_claims"] and m["has_specification"]
    assert m["abstract_within_150w"] is True
    assert m["claims"]["independent"] >= 1
    assert m["output_char_count"] > 0
    assert m["output_word_count"] > 0


def test_summarize_empty_output() -> None:
    m = summarize_auto_metrics("")
    assert m["has_abstract"] is False
    assert m["claims"]["total"] == 0
    assert m["abstract_within_150w"] is False

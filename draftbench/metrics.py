"""Layer 1 automatic metrics — structural, no-expertise-required.

Maps to METHODOLOGY.md §6 Layer 1 (regex + parser, no LLM). Layers 2/4/5
(LLM-judge §112 / jurisdictional / hallucination) live in `draftbench.evaluator`.

v1 scope:
- Section presence (ABSTRACT / CLAIMS / SPECIFICATION)
- Claim count (independent + dependent)
- Abstract word count vs. MPEP 608.01(b) 150-word limit
- Output character / word count

v1.1+ planned:
- BERTScore against Track A ground-truth claims
- MPEP 608.01(a) section-order validation
- Antecedent-basis chain validation per claim
- Markush group structural correctness (chemistry)
"""

from __future__ import annotations

import re

CLAIM_LINE_RE = re.compile(r"^\s*(\d+)\.\s+", re.MULTILINE)
SECTION_RE = re.compile(r"===\s*(ABSTRACT|CLAIMS|SPECIFICATION)\s*===", re.IGNORECASE)


def extract_section(text: str, name: str) -> str:
    """Return the content of a `=== SECTION ===` block by name, or empty string."""
    pattern = re.compile(
        rf"===\s*{name}\s*===\s*(.*?)(?=\n===\s*\w+\s*===|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def extract_claim_count(text: str) -> dict[str, int]:
    """Count total / independent / dependent claims in the CLAIMS section."""
    claims_section = extract_section(text, "CLAIMS")
    if not claims_section:
        return {"total": 0, "independent": 0, "dependent": 0}

    claim_numbers = [int(m.group(1)) for m in CLAIM_LINE_RE.finditer(claims_section)]
    total = len(claim_numbers)

    dependent = sum(
        1 for _ in re.finditer(r"(?im)^\s*\d+\.\s+.*?of\s+claim\s+\d+", claims_section)
    )
    independent = max(total - dependent, 0)

    return {"total": total, "independent": independent, "dependent": dependent}


def count_sections(text: str) -> dict[str, bool]:
    """Detect which of the three required sections are present in the output."""
    found = {s.upper() for s in SECTION_RE.findall(text)}
    return {
        "has_abstract": "ABSTRACT" in found,
        "has_claims": "CLAIMS" in found,
        "has_specification": "SPECIFICATION" in found,
    }


def abstract_word_count(text: str) -> int:
    abstract = extract_section(text, "ABSTRACT")
    return len(abstract.split()) if abstract else 0


def summarize_auto_metrics(output_text: str) -> dict:
    """Compute the full Layer 1 metric bundle for a single draft."""
    sections = count_sections(output_text)
    claims = extract_claim_count(output_text)
    abs_words = abstract_word_count(output_text)
    return {
        **sections,
        "claims": claims,
        "abstract_word_count": abs_words,
        "abstract_within_150w": 0 < abs_words <= 150,
        "output_char_count": len(output_text),
        "output_word_count": len(output_text.split()),
    }

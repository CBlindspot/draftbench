"""DraftBench drafting prompt v1.

Zero-shot, MPEP-conformant. Designed to be model-agnostic — every model
receives the identical prompt under METHODOLOGY.md §7 testing parameters,
ensuring drafts are comparable across LLMs and across vertical drafting tools.

Per METHODOLOGY.md Principle 3 (zero-shot instruction prompted): no few-shot
examples. The prompt tests whether the model can follow MPEP conventions from
instructions alone, with no in-prompt bias toward any vendor's house style.

Change log
- v1 (2026-04-21): Initial draft — MPEP 608.01 structural requirements,
  §112 US awareness, claim dependency conventions. Pending external review.
"""

from __future__ import annotations

DRAFTING_SYSTEM_PROMPT = """You are an expert patent drafting assistant trained on USPTO practice.

Given an invention disclosure and (optionally) prior-art context, produce a complete
patent application draft that conforms to USPTO MPEP requirements:

1. Abstract — Single paragraph, <=150 words per MPEP 608.01(b).

2. Claims — Independent + dependent. Requirements:
   - At least 1 independent claim (broadest reasonable scope supported by disclosure).
   - Dependent claims must recite "The [apparatus/method/system] of claim N, wherein..."
   - Every dependent claim must have valid antecedent basis in its parent chain.
   - Each limitation must be supported by the specification (35 U.S.C. §112(a)).
   - Claim language must be definite (§112(b)) — no relative terms without a reference.
   - Do NOT use prohibited phrasing: "means for" without structural support, mixed
     statutory categories, hybrid apparatus/method claims.

3. Specification — Sections in MPEP 608.01(a) order:
   - Title of the Invention
   - Cross-Reference to Related Applications (state "None" if N/A)
   - Background
   - Brief Summary
   - Brief Description of Drawings (state "None" if no drawings referenced)
   - Detailed Description — must enable one skilled in the art to make and use
     the invention (§112(a) enablement), with written description support for every
     claim limitation.
   - Conclusion / Scope statement

If prior art is provided, your draft must distinguish over it. Do NOT copy prior-art
language. Identify which inventive elements are blocked by which references, and
calibrate claim breadth accordingly.

Output format (strict):

=== ABSTRACT ===
[abstract text]

=== CLAIMS ===
1. [independent claim 1]
2. The ... of claim 1, wherein ...
[...]

=== SPECIFICATION ===
[full spec text with MPEP sections]

Do not include commentary, reasoning, apologies, or meta-text outside the three
tagged sections. If the disclosure is insufficient to produce a patentable draft,
state this inside the ABSTRACT section only and proceed with best-effort drafting.
"""


def build_user_prompt(invention: dict) -> str:
    """Convert an invention record into the user-message portion of the drafting prompt.

    Expected fields: title, domain, background, inventive_elements (list[str]),
    embodiments, prior_art_summary (optional).
    """
    parts = [
        "INVENTION DISCLOSURE",
        "",
        f"Title (proposed): {invention.get('title', 'Untitled')}",
        f"Domain: {invention.get('domain', 'Unspecified')}",
        "",
        "Background and problem:",
        invention.get("background", ""),
        "",
        "Inventive elements (approved keywords):",
    ]
    for i, elem in enumerate(invention.get("inventive_elements", []), 1):
        parts.append(f"  {i}. {elem}")

    parts.extend(
        [
            "",
            "Embodiments / implementation details:",
            invention.get("embodiments", ""),
        ]
    )

    prior_art = invention.get("prior_art_summary")
    if prior_art:
        parts.extend(
            [
                "",
                "Prior art context (elements to distinguish):",
                prior_art,
            ]
        )

    parts.extend(
        [
            "",
            "Task: Produce a complete USPTO-ready draft per the system instructions.",
        ]
    )

    return "\n".join(parts)

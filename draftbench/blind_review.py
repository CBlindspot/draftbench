"""Export blind-review packages for the human panel (Track B).

Per METHODOLOGY.md §3.2:
    1. Drafts exported with letter IDs (A, B, C, ...).
    2. Mapping file (`letter → model`) segregated from review package.
    3. Reviewers rate independently against rubrics in `data/rubrics/*.json`.
    4. De-anonymization happens only after scoring + forced-rank passes complete.

Each draft becomes a single .txt file under `out_dir/<reviewer>/{invention}_{letter}.txt`.
The `_mapping.json` lives at `out_dir/_mapping.json` and is the only file with the
letter→model mapping; reviewers receive a copy of `out_dir/<reviewer>/` only.
"""

from __future__ import annotations

import json
from pathlib import Path


def write_blind_review_package(
    drafts: list[dict],
    out_dir: str | Path,
    reviewers: list[str] | None = None,
) -> Path:
    """Write blind-review .txt files + a segregated mapping.json.

    Letter assignment is deterministic per (invention, model) pair so the same
    model gets the same letter across reviewers — necessary for forced-rank
    aggregation.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Group succeeded drafts by invention.
    by_invention: dict[str, list[dict]] = {}
    for d in drafts:
        if not d.get("succeeded"):
            continue
        by_invention.setdefault(d["invention_id"], []).append(d)

    # Deterministic letter assignment per invention: sort by model_name then by repeat.
    mapping: dict[str, dict[str, str]] = {}
    letter_assignments: dict[str, dict[tuple[str, int], str]] = {}
    for inv_id, rows in by_invention.items():
        rows.sort(key=lambda r: (r["model_name"], r.get("repeat", 0)))
        mapping[inv_id] = {}
        letter_assignments[inv_id] = {}
        for i, r in enumerate(rows):
            letter = _letter_for_index(i)
            key = (r["model_name"], r.get("repeat", 0))
            letter_assignments[inv_id][key] = letter
            mapping[inv_id][letter] = f"{r['model_name']}#repeat{r.get('repeat', 0)}"

    # Targets: one folder per reviewer, or a single folder if no reviewers given.
    targets = list(reviewers) if reviewers else ["all"]
    for reviewer in targets:
        reviewer_dir = out / reviewer
        reviewer_dir.mkdir(parents=True, exist_ok=True)
        for inv_id, rows in by_invention.items():
            for r in rows:
                letter = letter_assignments[inv_id][(r["model_name"], r.get("repeat", 0))]
                fname = reviewer_dir / f"{inv_id}_{letter}.txt"
                header = (
                    f"# {r.get('invention_title', '')}\n"
                    f"# Output ID: {letter} (blind)\n"
                    f"# Reviewer: {reviewer}\n\n"
                )
                fname.write_text(header + (r.get("output_text") or "(no output)"), encoding="utf-8")

    (out / "_mapping.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    return out


def _letter_for_index(i: int) -> str:
    """0 → A, 25 → Z, 26 → AA, 27 → AB, ... — supports >26 candidates per invention."""
    if i < 26:
        return chr(ord("A") + i)
    return _letter_for_index(i // 26 - 1) + chr(ord("A") + (i % 26))

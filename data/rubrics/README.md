# DraftBench Rubrics

One rubric per dimension (1-7 per METHODOLOGY.md §4). Each rubric is a JSON document scored on a 1-5 scale by both Track A (auto + ground truth comparison) and Track B (registered patent attorneys, blind).

## File naming

`dim{N}_{snake_case_dimension_name}.json`

| File | Dimension | Weight |
|---|---|---:|
| `dim1_claim_drafting_quality.json` | Claim Drafting Quality | 35% |
| `dim2_specification_quality.json` | Specification Quality | 20% |
| `dim3_durability.json` | Prosecution & Post-Grant Durability | 15% |
| `dim4_workflow_ux.json` | Workflow & UX | 10% |
| `dim5_safety_fabrication.json` | AI Safety & Fabrication Resistance | 10% |
| `dim6_confidentiality.json` | Confidentiality, Privilege & Trust | 5% |
| `dim7_integration_tco.json` | Integration & TCO | 5% |

## Schema

```json
{
  "dimension_id": 1,
  "dimension": "Claim Drafting Quality",
  "weight": 0.35,
  "version": "1.0-draft",
  "description": "What this dimension measures, in one paragraph.",
  "sub_criteria": [
    "Independent-claim scope appropriateness",
    "Independent/dependent claim architecture",
    "..."
  ],
  "scoring_levels": [
    {
      "score": 5,
      "label": "Excellent",
      "criteria": "Concrete description of what a 5/5 looks like.",
      "anchor_example": "An optional excerpt or pointer to data/anchors/ illustrating this score."
    },
    {
      "score": 4,
      "label": "Good",
      "criteria": "...",
      "anchor_example": "..."
    },
    {
      "score": 3,
      "label": "Adequate",
      "criteria": "...",
      "anchor_example": "..."
    },
    {
      "score": 2,
      "label": "Weak",
      "criteria": "...",
      "anchor_example": "..."
    },
    {
      "score": 1,
      "label": "Unacceptable",
      "criteria": "...",
      "anchor_example": "..."
    }
  ],
  "track_a_signals": [
    "BERTScore against ground-truth independent claims",
    "Coverage of survived claim limitations"
  ],
  "track_b_protocol": "Reviewer reads draft + reference disclosure, scores 1-5, optionally provides forced-rank across all candidates for the same invention.",
  "kill_switch": null
}
```

## Status (v1.0-draft)

The rubric files in this directory ship as **skeletons** for v1.0 INTA — schema and dimension framing are locked, but the 1-5 anchor criteria are placeholder text pending external review per METHODOLOGY.md §16 open questions.

Full anchored rubrics with at least one validated example per score level land in v1.1.

## Adding or modifying a rubric

See [CONTRIBUTING.md](../../CONTRIBUTING.md). Rubric changes follow the SemVer policy in METHODOLOGY.md §13 — sub-criteria additions are MINOR, weighting changes are MAJOR.

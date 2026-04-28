# DraftBench Full Test Corpus — v1.1+

This directory will hold the full DraftBench test corpus per METHODOLOGY.md §3.1:

- **50 IPR-survived patents** reverse-engineered into disclosure inputs + ground-truth claims/specs
- **Stratified across 10 domains**: mechanical, medtech, software, chemistry, biotech, semiconductor, materials, AI/ML, communications, energy
- **Provenance categories**:
  - `reverse_engineered_uspto` — disclosure portion only, claims segregated as ground truth
  - `synthetic_public_domain` — held-out contamination-control set
  - `post_2024_publications` — partial hold-out for training-cutoff testing

Build is scoped to v1.1 (August 2026 target). The corpus build is a 3-6 month effort by Satermo / Hansra with manual claim/disclosure separation. Track A scoring depends on this corpus.

## Until v1.1 lands

For v1.0 INTA, runs are executed against the [`mini` set](../mini/) only. The first public run is captured under [`v1.0-first-public-run/`](../v1.0-first-public-run/).

## Structure (planned)

```
full/
├── mechanical/      # 5 patents per domain target
├── medtech/
├── software/
├── chemistry/
├── biotech/
├── semiconductor/
├── materials/
├── ai_ml/
├── communications/
└── energy/
    ├── invention_<patent_id>.jsonl      # disclosure input
    └── groundtruth_<patent_id>.jsonl    # survived claims + spec sections
```

Ground-truth files are not included in the harness drafting input — they are loaded by the Track A scorer only.

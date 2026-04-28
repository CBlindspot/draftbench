# Implementation Checklist — DraftBench v1.0 INTA Release

**Target**: First public release at INTA 2026 (early May)
**Methodology version**: v1.0-draft (see `METHODOLOGY.md`)

This checklist tracks the items required to call DraftBench v1.0 publishable. v1.0 ships *methodology + harness + first run* — not full statistical claims. Statistical thresholds (Fleiss κ > 0.6, discrimination power, full Track A corpus) are scoped to v1.1+.

---

## Methodology — `METHODOLOGY.md`

- [x] Dual-track scoring (60% Track A historical + 40% Track B expert panel) defined
- [x] Seven weighted dimensions (35/20/15/10/10/5/5) defined with sub-criteria
- [x] Five-layer harness (structural / §112 US / [reserved human] / jurisdictional / hallucination + Therasense) defined
- [x] Testing parameters aligned with Artificial Analysis v4.0.4 with explicit divergences (§10)
- [x] Threats to validity + mitigations enumerated (§11)
- [x] Reporting format spec'd (§12)
- [x] SemVer versioning policy (§13)
- [x] Roadmap v1.0 → v2.0 (§14)
- [ ] Open question §16.1 — Track A weighting interpretation confirmation (Sacha)
- [ ] Open question §16.2 — Dim 4 attorney-edit-time protocol (Sylvain + reviewer panel)
- [ ] Open question §16.3 — Therasense kill-switch false-positive threshold calibration
- [ ] Open question §16.4 — Track A corpus query definition (50 IPR-survived patents)
- [ ] Open question §16.5 — third reviewer core panel slot (Sylvain via Questel)
- [ ] Open question §16.6 — academic review partner intro (Roger's collaborator)

## Reference Harness — `draftbench/`

### Phase 1 — Bootstrap (this release)
- [x] Package layout (`draftbench/`, `draftbench/models/`, `data/`, `scripts/`, `tests/`)
- [x] `BenchmarkRunner` — providers × inventions × repeats orchestrator
- [x] `BenchmarkResults` — JSON + CSV + blind-review folder export
- [x] OpenRouter adapter — single API key, unified pricing, broad model coverage
- [x] Drafting prompt v1 — MPEP 608.01 conformance, three-section output
- [x] Layer 1 auto-metrics — section presence, claim count, abstract word count
- [x] First public pilot run committed under `data/v1.0-first-public-run/`
- [x] CLI entry points scaffolded (`draftbench run`, `score`, `export-blind`, `report`)

### Phase 2 — v1.0 INTA-blocking
- [x] LLM-judge framework (`BaseJudge`, `OpenRouterJudge`, JSON parsing, structured `JudgeResult`)
- [x] Layer 2 §112 US LLM-judge (cross-family Claude ↔ GPT supported via `cross_judge=` parameter)
- [x] Layer 5A — Therasense kill-switch (USPTO Patent Public Search via PatentsView API + Google Patents fallback + disk cache)
- [x] Layer 5B — Hallucination Classes B-E LLM-judge (taxonomy parser, per-class counts)
- [x] Layer 4 — Jurisdictional EP/CN/JP LLM-judge (single-call combined verdict, weighted merge)
- [x] Composite scorer — 7-dim weighted merge with Therasense kill-switch hard floor (v1.0 partial: dims 1+2+5 scored, 3/4/6/7 deferred)
- [x] Blind-review package generator with mapping-file segregation
- [x] HTML report generator with Pareto plot (cost × quality), per-dim breakdown, kill-switch findings, sortable leaderboard
- [x] CLI integration — `draftbench score` runs all layers, `draftbench report` renders HTML

### Phase 3 — v1.1 (post-INTA)
- [ ] Track A corpus pipeline — Juristat API integration, 50 IPR-survived patents, ground-truth claim/spec extraction
- [ ] Fleiss κ inter-rater reliability calculator
- [ ] Stratified review-package sampler (each reviewer sees 2 inventions full + 1 partial)
- [ ] Quarterly DraftBench Report template

## Rubrics — `data/rubrics/dim{1-7}_*.json`

- [x] Schema definition (`data/rubrics/README.md`)
- [ ] Dim 1 — Claim Drafting Quality (5-level rubric, anchor examples)
- [ ] Dim 2 — Specification Quality (5-level rubric, jurisdiction-aware)
- [ ] Dim 3 — Prosecution & Post-Grant Durability (5-level rubric)
- [ ] Dim 4 — Workflow & UX (edit-time measurement protocol)
- [ ] Dim 5 — AI Safety & Fabrication Resistance (5-class taxonomy + Therasense criteria)
- [ ] Dim 6 — Confidentiality, Privilege & Trust (4 binary deal-breakers)
- [ ] Dim 7 — Integration & TCO (3-year cost model)

## Test Inventions — `data/`

- [x] Mini case — one anonymized public-domain mechanical invention (`data/mini/`)
- [x] First-public-run dataset (anonymized pilot disclosures)
- [ ] v1.1 corpus — 50 IPR-survived patents reverse-engineered, stratified across 10 domains
- [ ] v1.1 contamination-canary subset (post-2024 USPTO publications)
- [ ] v1.1 synthetic-invention subset (no USPTO provenance, contamination-controlled)

## Panel — Track B reviewers

- [ ] Reviewer 1 — Satermo (confirmed)
- [ ] Reviewer 2 — Hansra (confirmed)
- [ ] Reviewer 3 — TBC US-primary general-technology (Sylvain via Questel — pending)
- [ ] Specialist panel chairs (chemistry / AI-ML / biotech / medical device — announced v1.0, staffed v1.1)
- [ ] Honoraria framework — $3-5K per attorney per run, per-run NDA template

## Documentation

- [x] `README.md` — overview + quick start + leaderboard placeholder
- [x] `METHODOLOGY.md` — full versioned methodology
- [x] `MANIFESTO.md` — why DraftBench exists, addressed to industry
- [x] `CONTRIBUTING.md` — test invention / rubric / adapter contribution guidelines
- [x] `INTEGRATION.md` — adapter patterns (API / CSV / browser)
- [x] `data/rubrics/README.md` — rubric JSON schema specification (skeleton anchor criteria pending Sylvain + Roger's academic partner review)
- [x] `data/full/README.md` — Track A corpus organization placeholder (v1.1 build target)
- [ ] `reports/v1.0-summary.md` — first public run scorecard (generated post full-run via `draftbench report`)

## Infrastructure

- [x] LICENSE Apache-2.0
- [x] `pyproject.toml` (hatchling) with optional provider dependencies (anthropic / google / playwright forward-declared for future adapters)
- [x] `.gitignore`
- [x] `.github/workflows/ci.yml` — pytest + ruff + mypy
- [x] `tests/` — 73 tests covering harness, adapters, evaluator, judges, layers, scoring, USPTO client (Layer 1-5 paths + kill-switch + JSON parsing + composite math + report rendering)
- [ ] `pip install draftbench` published to PyPI (post-v1.0)

## Pre-Launch Validation

- [ ] Mini-run sanity check — 1 invention × 4 frontier models × 1 repeat completes end-to-end (pending OpenRouter top-up)
- [ ] Full v1.0 first run — 7 LLMs × 3 inventions × 3 repeats = 63 drafts
- [ ] Methodology academic-partner review (Roger's collaborator)
- [ ] Vendor co-announcement coordination with PatentBench (joint INTA reveal)

---

*Last updated: 2026-04-28 — Phase 2 complete (LLM-judge framework, Layers 2/4/5A/5B, composite scorer, HTML report, CLI `score` + `report`). 73 tests passing. Awaiting OpenRouter top-up for full v1.0 first-run, Sacha + academic + Sylvain methodology review, and §16 open-question resolutions.*

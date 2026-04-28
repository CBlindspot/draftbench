# DraftBench Methodology

**Version** : v1.0-draft (2026-04-23, pending Sylvain + Roger's academic partner review)
**Scope** : Patent drafting — Steps 9-11 of a typical prosecution workflow (prior-art mapping, claim generation, specification + abstract drafting)
**Authors** : CBlindspot (Andy Garcia, Sacha), with input from Sylvain Chevallier (CPO IP, Riseon), Roger Hahn (PatentBench)
**License** : Apache-2.0 — same as the repository

---

## 1. Why a public benchmark for patent drafting

### 1.1 The gap

As of early 2026, no independent, reproducible benchmark exists for AI-assisted patent drafting. Every vertical tool (DeepIP, Solve Intelligence, Patlytics, IP Author, Rowan Patents, Ankar) publishes marketing claims about draft quality. None is verifiable by a third party. Meanwhile, frontier general-purpose LLMs with retrieval and prompt engineering may or may not match these tools — the comparison has never been run under a shared protocol.

The closest public benchmark relevant to this work is [Artificial Analysis Intelligence Index v4.0.4](https://artificialanalysis.ai/methodology/intelligence-benchmarking), which covers reasoning, knowledge, maths, coding and agentic tasks across 10 evaluations. None measures patent drafting quality. The nearest proxies — CritPt (physics reasoning) and GDPval-AA (agentic task completion) — score frontier models at 0-30% and 30-55% respectively, with no decomposition over legal-technical drafting.

### 1.2 Why open-source the methodology

A vendor that publishes its own benchmark is structurally accused of "benchmaxxing". A vendor that publishes a versioned, open methodology, with an independent reference harness, that any third party can execute and reproduce, has a different defensibility profile — the same defensibility profile that [PatentBench](https://github.com/rhahn28/patentbench) has established for prior-art search.

We take the same playbook for drafting.

### 1.3 Scope in the CBlindspot product

DraftBench is part of a two-tier benchmarking architecture within CBlindspot:

| Tier | Discover / Compare | Workflow Builder (DraftBench tier) |
|---|---|---|
| Question answered | "Which tools exist in this segment?" | "Of 3-5 shortlisted tools, which one do I sign?" |
| Volume | ~2000 products | 3-5 candidates per engagement |
| Scoring method | Metrics registry (universal + segment-specific + evidence tiers) | DraftBench / PatentBench / future benchmarks |
| Evidence tier | `claude_inference` (0.5) to `vendor_doc` (0.7) to `public_signal` (0.6) | `benchmark` (1.0) or `expert_review` (0.95) |
| Marginal cost per product | Near zero (LLM inference) | ~$15K + 15 hrs attorney-time per tool |
| Refresh cadence | Monthly to quarterly | Quarterly, subscription-based |
| Role | Scale play — surface of the iceberg | Credibility play — depth, backs decisions that matter |

Benchmarked products feed tier-1.0 evidence back into Discover. DraftBench is therefore not a separate product that lives next to Discover; it is the tier-1.0 input source for Discover when a tool has been formally benchmarked.

---

## 2. Principles (borrowed verbatim from Artificial Analysis v4.0.4)

We adopt AA's four principles because they are operationally sound and because alignment gives DraftBench results immediate comparability to a wider literature of LLM evaluation.

1. **Standardized** — all models evaluated under identical conditions: same prompt, same invention inputs, same temperature policy, same max output tokens.
2. **Unbiased** — evaluation techniques do not penalise models for answers that correctly follow the instructions. Robust output extraction, flexible scoring.
3. **Zero-shot instruction prompted** — we do NOT give few-shot examples in the drafting prompt. Tests the model's capacity to follow MPEP conventions from instructions alone. No in-prompt bias toward any vendor's house style.
4. **Transparent** — full methodology public (this document), harness source code public, anonymized raw outputs public, scoring rubrics public (`data/rubrics/*.json`).

---

## 3. Architecture — dual-track scoring

The DraftBench composite score is computed as:

```
Composite = 0.60 × TrackA_composite + 0.40 × TrackB_composite
```

Both tracks score the same seven weighted dimensions (see §4). The tracks differ only in the *source* of the scoring signal: historical ground-truth vs expert panel. Track A and Track B composite scores are always published **separately** alongside the merged composite — divergence between them is informative.

*(Pending Sacha confirmation: current interpretation is that both tracks score all 7 dims independently. Alternative interpretation where Track A scores only dim 3 Durability is explicitly rejected in v1.0 as it would collapse the methodology to a single-track design.)*

### 3.1 Track A — Historical ground truth (60% of composite)

Track A scores model-generated drafts against claims and specifications from patents that have **survived adversarial review**. The reference corpus is built once, at a heavy upfront cost, and reused indefinitely.

**Ground-truth weightings** (applied when computing Track A composite, higher weight for more rigorously validated patents):

| Survival event | Weight |
|---|---:|
| PTAB-survived IPR (final written decision, claim maintained) | 5.0× |
| Commercially validated (licensed in arm's-length deal, enforced in settlement, sold in M&A diligence) | 3.0× |
| Reexamination survived (USPTO ex parte / inter partes) or EPO opposition survived | 2.5× |
| Expert-panel-drafted (drafted by a pre-specified panel of registered patent attorneys, no adversarial history) | 1.5× |
| Granted, unchallenged (no IPR, no reexam, no commercial validation) | 1.0× |

**Corpus construction protocol** (Step 1 in §5):

1. Select a patent with a qualifying survival event.
2. Split into disclosure + claims. Keep only the disclosure.
3. Redact any text that references the claims ("as claimed", "the claims include", claim numbers). Manual pass by Satermo / Hansra.
4. The disclosure becomes an input to the harness. The claims become the ground-truth reference.

**Scoring the 7 dimensions in Track A**: for each draft generated from the redacted disclosure, we compute a per-dimension similarity + coverage score against the ground-truth claims and specification. For example:

- Dim 1 Claim Drafting Quality — overlap of independent claim scope, dependent-claim structural conformity to what survived
- Dim 2 Specification Quality — §112 support for elements that were tested in the adversarial proceeding
- Dim 3 Durability — reverse-engineered from the survival event itself (inherently Track A)
- Dims 4-7 — Track A has limited signal on workflow, safety, confidentiality, integration (vendor-level metrics); these lean heavily on Track B

Target corpus size for v1.0: **50 IPR-survived patents** reverse-engineered. This is a 3-6 month build, not a per-run cost. v1.1 and subsequent versions extend the corpus without re-running setup.

### 3.2 Track B — Expert blind review (40% of composite)

Three registered patent attorneys blind-rate each draft across the seven weighted dimensions. Panel composition for v1.0: **Satermo, Hansra, and one TBC specialist** (see §4.8 panel structure).

**Blind protocol**:

1. Drafts exported with letter IDs (A, B, C, …).
2. Mapping file (`letter → model`) segregated from review package.
3. Each reviewer rates independently across the 7 dimensions, using rubrics in `data/rubrics/*.json`.
4. Reviewers also provide a forced-rank of all outputs for the same invention (used for dim 1 "preferred ranking" signal).
5. De-anonymization happens only after scoring pass 1 + forced-rank pass 2 are both complete for all 3 reviewers.

**Inter-rater reliability**: Fleiss κ reported for every run on the structural dimensions (1, 2) and the forced-rank. Target κ > 0.6 for v1.1 publishability.

**Per-reviewer load**: 5 hours per attorney per run. Honoraria: $3-5K per attorney per run.

---

## 4. The seven dimensions

Each dimension is scored in both Track A and Track B using the same rubric (published in `data/rubrics/dim{N}_{name}.json`).

| # | Dimension | Weight | What it measures |
|:---:|---|---:|---|
| 1 | **Claim Drafting Quality** | 35% | Strategically sound and legally durable claims — scope, independent/dependent architecture, differentiation from prior art, Markush correctness where applicable |
| 2 | **Specification Quality** | 20% | §112(a)/(b)/(f) US conformance + equivalents EP (Art 83/84/123(2)), CN (Art 26), JP (Art 36) — jurisdictional conformity per use case |
| 3 | **Prosecution & Post-Grant Durability** | 15% | Adversarial-survival prediction (Juristat, Lex Machina, Darts-ip) + comparison to ground-truth historical |
| 4 | **Workflow & UX** | 10% | Attorney-edit-time in minutes — the commercial metric that decides senior-partner adoption |
| 5 | **AI Safety & Fabrication Resistance** | 10% | 5-class hallucination taxonomy + Therasense kill-switch (zero tolerance on fabricated prior-art citations) |
| 6 | **Confidentiality, Privilege & Trust** | 5% | Four binary deal-breakers — privilege-preserving evaluation, no-train-on-data, air-gap option, audit logs |
| 7 | **Integration & TCO** | 5% | MCP/API integration, total cost over 3 years (license + infrastructure + maintenance + switching) |

### 4.1 Sub-criteria per dimension

**Dim 1 — Claim Drafting Quality (35%)**
- Independent-claim scope appropriateness (too broad → unenforceable ; too narrow → designed-around)
- Independent/dependent claim architecture depth and hierarchy
- Differentiation from cited prior art (§103 nonobviousness-aware drafting)
- Markush group correctness where applicable (chemistry / mechanical)
- Antecedent basis hygiene (every "the [noun]" has a prior definite introduction)

**Dim 2 — Specification Quality (20%)**
- §112(a) enablement (teaching a POSITA to make and use)
- §112(b) definiteness (clear claim terms, no ambiguity)
- §112(f) means-plus-function handling (disclosed structure corresponding to functional language)
- EP Art 83 sufficiency + Art 84 clarity / conciseness
- EP Art 123(2) added-matter screening (no new matter post-filing)
- CN Art 26.3/.4 sufficient-disclosure + clarity
- JP Art 36 enablement + clarity

**Dim 3 — Prosecution & Post-Grant Durability (15%)**
- Predicted survival probability (based on Track A ground truth comparison)
- Juristat API — claim-level prosecution outcome prediction
- Lex Machina — litigation outcome priors for analogous claims
- Darts-ip — worldwide litigation outcomes

**Dim 4 — Workflow & UX (10%)**
- Measured as attorney-edit-time in minutes per draft (lower is better)
- Captured by timed review sessions — attorney edits each anonymized draft to ship-ready state, edit-time logged
- Complementary metric: edit-distance (character-level diff between original draft and attorney-approved version)

**Dim 5 — AI Safety & Fabrication Resistance (10%)**
5-class hallucination taxonomy:
- Class A — Fabricated prior-art citation (patent number / publication that does not exist) → **Therasense kill-switch**, instant fail
- Class B — Misattributed prior art (citation exists but does not teach what is claimed)
- Class C — Ungrounded technical claim (spec states a property not supported by disclosure)
- Class D — Inconsistent reference (disclosure internal contradiction)
- Class E — Overreach (claim scope outside what disclosure supports, §112(a) defect masked)

**Dim 6 — Confidentiality, Privilege & Trust (5%)**
Four binary deal-breakers (yes/no gates):
- Privilege-preserving evaluation (does the tool honor attorney-work-product doctrine on inputs)
- No-train-on-data (contractual + technical guarantee inputs are not used for model training)
- Air-gap / VPC option (tool deployable without external data egress)
- Audit logs (tamper-evident, RBAC-gated, retention-configured)

**Dim 7 — Integration & TCO (5%)**
- Integration vector (MCP server, REST API, plugin marketplace presence, enterprise SSO)
- License model (per-seat, per-draft, flat enterprise)
- Infrastructure cost (self-hosted GPU / cloud inference / vendor-managed)
- Maintenance cost (upgrades, new-model rollouts, regression testing)
- Switching cost (data export format, eval set portability, IP ownership of outputs)

---

## 5. Run schema

A DraftBench run consists of six steps. Three automatic, one human (the panel), one external (Juristat + adjacent APIs), one reporting.

| # | Step | Type | Time / resources |
|:---:|---|---|---|
| 1 | Test invention preparation (reverse-engineering of IPR-survived patents) | Setup — one-time, reusable | ~10 hrs per invention, by Satermo/Hansra, amortized across all future runs |
| 2 | Drafting in parallel across 4+ models / tools | Automatic — harness | ~30 min, OpenRouter-based, ~$15 compute for 4 models × 3 inventions × 3 repeats |
| 3 | Automatic scoring (Layers 1, 2, 4, 5 — structural, §112, jurisdictional, hallucination + Therasense kill-switch) | Automatic — harness | ~1 hr + 20% manual spot-check |
| 4a | Panel blind review (Track B) — prosecution-readiness, ship-readiness, Fleiss κ | Human — 3 attorneys | 5 hrs per attorney per run, $3-5K honoraria each |
| 4b | Ground-truth historical comparison (Track A) — Juristat API + overlap with survived claims | External — Juristat | ~1 hr API calls + Juristat license (budgetable) |
| 5 | Composite scorecard assembly + client report | Output — CBlindspot | ~1 day writeup, delivered in platform for continuous rerun |

Steps 4a and 4b run **in parallel**, not sequentially. Step 1 is the only one-time cost — the 10 hours of Satermo/Hansra per invention are reused for all future runs indefinitely. This is the economic backbone of the model: per-run cost decreases as the corpus grows.

**Total economic cost per benchmarked tool (v1.0 scale)**: ~$15K per tool, dominated by attorney honoraria (~$10-15K). Compute is negligible (~$15). Juristat license is a fixed subscription, not per-run.

---

## 6. Harness architecture — 5 automated scoring layers

The automatic harness (Step 3) organizes scoring into five layers. Layer 3 is intentionally left as a no-op at the harness level — it is reserved for the human panel step, which runs outside the harness in step 4a.

| Layer | Scope | Maps to dimension(s) | Implementation |
|:---:|---|---|---|
| **1** | Structural — MPEP 608.01 section presence, claim count, abstract length, dependent-claim format, antecedent-basis proxy | Dim 1 (partial), Dim 2 (partial) | Regex + parser, no LLM call |
| **2** | §112 US — enablement, written description, definiteness, best mode | Dim 2 (US part) | LLM-judge cross-family (Claude judging GPT outputs and vice versa) |
| **3** | *[reserved for human panel — no automation]* | Dim 1 strategic, Dim 4 edit-time | Exported to blind-review package in step 4a |
| **4** | Jurisdictional — EP Art 83/84/123(2), CN Art 26, JP Art 36 | Dim 2 (international part) | LLM-judge with jurisdiction-specific rubric |
| **5** | Hallucination — 5-class taxonomy + Therasense kill-switch (fabricated prior-art citations instantly fail a draft) | Dim 5 | LLM-judge cross-family + USPTO Patent Public Search cross-reference for cited patent numbers |

Dimensions 6 (Confidentiality) and 7 (Integration/TCO) are **vendor-level metadata**, not per-draft scores. They are captured once per vendor at onboarding and refreshed quarterly.

---

## 7. Testing parameters

Aligned with Artificial Analysis v4.0.4 with the divergences listed in §10.

| Parameter | Value | Rationale |
|---|---|---|
| Temperature (non-reasoning) | 0 | Determinism for comparability |
| Temperature (reasoning) | 0.6 | AA-recommended for reasoning models |
| Max output tokens (non-reasoning) | 16,384 | AA default; average full spec + claims + abstract = 6-12K tokens |
| Max output tokens (reasoning) | Vendor maximum | Reasoning tokens + answer tokens combined |
| Retries on transient failure | 30 (exponential backoff 1s → 30s max) | AA default |
| Pass@1 scoring | Per-invention | AA default |
| Repeats per invention | 3 (v1.0), 5 (v1.1+ with attorney reviewers) | AA typical range |
| LLM judge (auto-scoring Layers 2, 4, 5) | Claude Opus 4.7 primary, GPT-5.4 cross-validation | Cross-family bias control |

---

## 8. Statistical validity thresholds

Three different statistical questions, three different thresholds. v1.0 does NOT claim to meet all of them — it publishes methodology + first exemplary run in the PatentBench style.

| Question | Threshold | Target version |
|---|---|:---:|
| Inter-rater reliability (Fleiss κ) | ~36 drafts scored by all 3 attorneys → κ significance. Target κ > 0.6. | **v1.1 (Aug 2026)** |
| Discrimination between tools (statistical power) | ~64 drafts per tool for effect size d=0.5 with 80% power. At 4 tools = ~256 drafts, ~22 runs. | **v1.2 (Nov 2026)** |
| External validity (Track A) | ~50 IPR-survived patents reverse-engineered, one-time build. | **v1.1 ongoing build** |

**v1.0 (INTA May 2026)**: methodology published + 1 run exemplaire (the anonymized first-public-pilot run). No statistical claims. Framing: "methodology + first example" following the PatentBench template.

---

## 9. Panel structure — two-tier

For v1.0 we announce a two-tier panel structure and staff it over v1.1-v1.2:

**Core panel (v1.0)** — 3 attorneys:
- Satermo
- Hansra
- Third reviewer, US-primary general-technology (TBC, Questel-sourced by Sylvain)

**Specialist panels (announced v1.0, staffed v1.1)** — per-domain panels for:
- Chemistry
- AI / ML
- Biotech
- Medical device

Assignment logic: each invention is categorized into one domain. The core panel scores every run. The relevant specialist panel joins for runs that materially touch that domain.

This structure forces the conversation onto rigor rather than panel size. A 3-person core panel with 4 specialist panels is more scientifically defensible than a 10-person undifferentiated panel.

---

## 10. Divergences from AA methodology (explicit)

| Item | AA v4.0.4 | DraftBench v1.0 | Why |
|---|---|---|---|
| Max output tokens (non-reasoning) | 16,384 | 16,384 | Same |
| Scoring | Pass@1 aggregated | Pass@1 (automatic) + forced-rank (human) + ground-truth similarity (Track A) | Patent drafting has no single objective answer |
| Equality checker LLM | GPT-4o (Aug) | Claude Opus 4.7 primary, GPT-5.4 cross-check | Current frontier; cross-family bias control |
| Repeats | 1-10 depending on eval | 3 for v1.0 (budget), 5 for v1.1+ | Same range, phased rollout |
| Reasoning tokens | Measured separately | Measured, folded into latency + cost | Unified performance view matters more than isolating reasoning time for IP clients |
| Dual-track scoring | Single-track (eval-level) | Dual-track (historical ground-truth + expert panel), 60/40 merge | Protects against both "subjective panel" and "stale-ground-truth" attacks |

---

## 11. Threats to validity + mitigation

1. **Test-set leakage** — public USPTO patents may appear in model training data, inflating Track A scores on reverse-engineered inventions.
   *Mitigation*: (a) use synthetic inventions for a subset of the test set, (b) include post-2024 USPTO publications as partial hold-out, (c) request anonymized pilot-partner disclosures for v1.0 first run (ground-truth not in any training corpus).

2. **Judge bias** — LLM judges may favor their own family.
   *Mitigation*: cross-family judges (Claude judging GPT and vice versa); human overlap on 30% of samples; publish per-judge-family score breakdown alongside the merged score.

3. **Prompt sensitivity** — single prompt template may favor some model families.
   *Mitigation*: v1.1 introduces three prompt variations ("MPEP-style", "claim-first", "spec-first") to measure per-model robustness.

4. **Reviewer fatigue** — 3 reviewers × 3 inventions × 7-12 draft sources = 63-108 drafts per reviewer.
   *Mitigation*: stratified sampling — each reviewer sees 2 inventions fully, 1 partially. Power analysis targets α=0.05, β=0.2 for detecting a 10-point gap in composite ranking.

5. **API endpoint variance** — OpenRouter routes to multiple providers per model ; two runs on Llama 3.3 70B may hit different backends with different throughput / quality.
   *Mitigation*: record `raw_response.model_used` per call ; re-run on flagged providers if variance > 20%.

6. **Track A corpus sampling bias** — the ~50 IPR-survived patents may over-represent specific domains or prosecution styles.
   *Mitigation*: stratified corpus construction across 10 technology areas (mechanical, medtech, software, chemistry, biotech, semiconductor, materials, AI/ML, communications, energy). Report corpus composition in every run.

7. **Therasense kill-switch over-triggering** — aggressive fabrication detection may false-positive on legitimate but unusual prior-art citations.
   *Mitigation*: manual spot-check of 100% of kill-switch triggers in the first 10 runs ; calibrate threshold based on false-positive rate.

---

## 12. Reporting format

### 12.1 Per invention × model × repeat

Artifact: one `results/run_{timestamp}/invention_{id}/model_{name}/repeat_{k}.json` with full output + auto-metrics + raw API response.

### 12.2 Per run

- `results/run_{timestamp}/summary.csv` — flat table, one row per (invention, model, repeat).
- `results/run_{timestamp}/composite.csv` — one row per (invention, model), composite score + per-dimension breakdown + Track A + Track B components.
- `results/run_{timestamp}/review/` — blind packages for human review, one letter-ID folder per draft.
- `results/run_{timestamp}/report.html` — shareable scorecard with Pareto plots (cost × quality, throughput × quality, per-dimension radar chart).

### 12.3 Quarterly DraftBench Report (v1.1+)

- Aggregate across all runs since last quarterly report.
- Vendor leaderboard with 95% CI.
- Model drift analysis (same model evaluated quarter-over-quarter).
- Methodology changelog.

---

## 13. Versioning

SemVer applied to the methodology:

- **MAJOR** (v1 → v2) — breaking changes to dimension structure, weightings, or Track A/B definition. Requires 60-day public comment period + academic partner sign-off.
- **MINOR** (v1.0 → v1.1) — new corpus additions, new model adapters, new sub-criteria. Backward-compatible scoring.
- **PATCH** (v1.0 → v1.0.1) — rubric text clarifications, prompt wording fixes, typo corrections.

Every version is tagged in the repository. Historical runs remain reproducible against the methodology version they were executed under.

---

## 14. Roadmap

| Version | Target | Scope |
|---|---|---|
| **v1.0** | INTA 2026 (May) | Methodology published, harness released, first public run (7 LLMs × 3 anonymized inventions × 3 repeats), specialist panel structure announced |
| v1.1 | August 2026 | Fleiss κ > 0.6 achieved on 36 drafts, Track A corpus at 50 IPR-survived patents, first Quarterly DraftBench Report, specialist panels staffed (chemistry + AI/ML) |
| v1.2 | November 2026 | 5 vertical tools added (DeepIP, Solve, Patlytics, IP Author, Rowan), 60-80 drafts, Track A fully integrated in composite, vendor-named comparison publishable |
| v2.0 | April 2027 | 200+ drafts, 10+ tools, 10 stratified domains, academic journal submission (target: Berkeley Technology Law Journal, Harvard JOLT, or similar) |

---

## 15. References

### 15.1 Benchmarks and standards

- Artificial Analysis Intelligence Index v4.0.4 — https://artificialanalysis.ai/methodology/intelligence-benchmarking
- AA Performance methodology — https://artificialanalysis.ai/methodology/performance-benchmarking
- AA Agentic methodology (AA-AgentPerf) — https://artificialanalysis.ai/methodology/agentperf
- PatentBench (Roger Hahn) — https://github.com/rhahn28/patentbench

### 15.2 Legal / jurisdictional

- USPTO MPEP 608.01 — abstract, claims, specification format
- 35 USC §112 — specification requirements (a) enablement, (b) definiteness, (f) means-plus-function
- EPC Art 83, 84, 123(2) — sufficient disclosure, clarity, added-matter
- SIPO Patent Law Art 26 (China) — sufficient disclosure + clarity
- JPO Patent Act Art 36 (Japan) — enablement + clarity
- *Therasense v. Becton Dickinson* (Fed. Cir. 2011) — inequitable conduct doctrine applied to material misrepresentation of prior art

### 15.3 Commercial data providers (Track A)

- Juristat — USPTO prosecution outcome data + PTAB decisions
- Lex Machina — district court patent litigation outcomes
- Darts-ip — worldwide litigation outcomes

### 15.4 Related CBlindspot work

- PatentVest pilot run — first public DraftBench v1.0 run, anonymized
- DraftBench repository — https://github.com/cblindspot/draftbench
- CBlindspot platform — https://cblindspot.ai

---

## 16. Open questions for review

*(To be resolved before v1.0 final publication.)*

1. **Track A weighting interpretation** — current interpretation has both tracks scoring all 7 dimensions with a 60/40 composite merge. Alternative interpretation (Track A = only Dim 3 Durability scored at 60% of composite) is rejected in this draft. *Requires Sacha confirmation.*
2. **Dim 4 Workflow & UX measurement protocol** — timed attorney-edit sessions require an operational setup (stopwatch, approved edit format) that is not yet defined. *Requires Sylvain + reviewer panel input.*
3. **Dim 5 Therasense kill-switch false-positive rate** — calibration threshold depends on first 10 runs ; v1.0 ships with a conservative default. *Empirical, resolves v1.1.*
4. **Track A corpus composition** — 50 IPR-survived patents stratified across 10 domains requires Juristat query definition and manual curation. *Build starts post-INTA, v1.1 delivery.*
5. **Third-reviewer core panel slot** — TBC pending Sylvain's Questel-sourcing. *Required before v1.0 first run publication.*
6. **Academic review partner** — Roger's academic collaborator (law professor) to review methodology before v1.0 publication. *Intro pending partnership formalization.*

---

*CBlindspot · DraftBench v1.0-draft · 2026-04-23*

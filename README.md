# DraftBench

**An open-source benchmark for AI-assisted patent drafting.**

Version 1.0 · Co-announced with [PatentBench](https://github.com/rhahn28/patentbench) at INTA 2026 · Apache-2.0

---

## What is DraftBench

DraftBench is an open standard for evaluating the quality of AI-generated patent drafts — claims, specifications, and abstracts. It publishes a versioned methodology, a reference test harness, and a dual-track scoring protocol that measures both *historical durability* (against patents that have survived adversarial review) and *expert preference* (blind-rated by a panel of registered patent attorneys).

DraftBench is a **vertical deep-dive on pre-filing patent drafting**, complementary to [PatentBench](https://github.com/rhahn28/patentbench)'s **horizontal coverage of patent prosecution AI** across five domains (Administration, Drafting, Prosecution, Analytics, Prior Art). Where PatentBench measures post-filing claim amendment, DraftBench measures pre-filing application drafting. Together they form the beginning of an open ecosystem of IP workflow benchmarks — because *evaluation should not be a marketing claim*.

---

## Why this exists

As of early 2026, no public benchmark exists for patent drafting quality. Every vertical drafting tool (DeepIP, Solve Intelligence, Patlytics, IP Author, Rowan Patents) publishes internal claims; none are independently verifiable. Meanwhile frontier LLMs — with appropriate prompting and retrieval — may or may not match these tools, and the comparison has never been run under a shared protocol.

DraftBench closes that gap. We publish the methodology. We release the harness. We run the benchmark in the open. Vendors integrate through a thin adapter layer. Results are reproducible by any third party.

**If a patent drafting tool is good, it should be willing to be measured.**

---

## How it works — dual-track scoring

A DraftBench run produces a composite score combining two complementary signals.

### Track A — Historical durability (60% of composite)

Claims in the test set are reverse-engineered from patents that have **survived adversarial review** (PTAB IPR, district court validity challenges, EPO oppositions, reexamination). The "correct" claims are by definition those that held up. Model-generated claims are scored against this ground truth.

Durability weightings:

| Source | Weight |
|---|---:|
| PTAB-survived IPR | 5.0× |
| Commercially validated (licensed, enforced, settled) | 3.0× |
| Reexamination / EPO opposition survived | 2.5× |
| Expert-panel-drafted | 1.5× |
| Granted, unchallenged | 1.0× |

### Track B — Expert blind review (40% of composite)

A panel of registered patent attorneys blind-rates drafts across seven weighted dimensions:

| # | Dimension | Weight | What it measures |
|:---:|---|---:|---|
| 1 | **Claim Drafting Quality** | 35% | Strategically sound and legally durable claims — scope, independent/dependent architecture, differentiation, Markush correctness where applicable |
| 2 | **Specification Quality** | 20% | §112(a)/(b)/(f) US conformance + equivalents EP (Art 83/84/123(2)), CN (Art 26), JP (Art 36) — jurisdictional conformity per use case |
| 3 | **Prosecution & Post-Grant Durability** | 15% | Track A — adversarial-survival prediction (Juristat, Lex Machina, Darts-ip) + comparison to ground-truth historical (IPR-survived patents) |
| 4 | **Workflow & UX** | 10% | Attorney-edit-time in minutes — the commercial metric that decides senior-partner adoption |
| 5 | **AI Safety & Fabrication Resistance** | 10% | 5-class hallucination taxonomy + Therasense kill-switch (zero tolerance on fabricated prior-art citations) |
| 6 | **Confidentiality, Privilege & Trust** | 5% | Four binary deal-breakers — privilege-preserving evaluation, no-train-on-data, air-gap option, audit logs |
| 7 | **Integration & TCO** | 5% | MCP/API integration, total cost over 3 years (license + infrastructure + maintenance + switching) |

Fleiss κ inter-rater agreement is published with every run.

### Why dual-track

Benchmarks that rely only on expert panels face accusations of subjective preference. Benchmarks that rely only on ground-truth comparisons take 5-10 years to reflect current art. DraftBench does both. When the two tracks diverge on a given model, *that divergence is itself the signal* — a model that scores high on Track B but low on Track A is producing drafts that feel good to attorneys but would not hold up in adversarial review. Publishing both scores separately, not only the composite, is what makes the benchmark defensible.

---

## Layered scoring

DraftBench evaluates each draft through five harness layers (see [METHODOLOGY.md §6](./METHODOLOGY.md)):

| Layer | Scope | Mechanism |
|:---:|---|---|
| 1 | Structural — MPEP 608.01 sections, claim count, abstract length | Regex + parser, no LLM |
| 2 | §112 US — enablement (a), definiteness (b), means-plus-function (f) | LLM-judge cross-family |
| 3 | *(reserved for the human panel — Track B blind review, no harness automation)* | Exported via `draftbench export-blind` |
| 4 | Jurisdictional — EP Art 83/84/123(2), CN Art 26, JP Art 36 | LLM-judge per jurisdiction |
| 5A | Therasense kill-switch — fabricated prior-art citation detection | USPTO Patent Public Search verification (PatentsView API + Google Patents fallback) |
| 5B | Hallucination Classes B-E — misattribution, ungrounded claims, inconsistency, overreach | LLM-judge with the 5-class taxonomy rubric |

Layer 5A's **Therasense kill-switch is non-negotiable**: any Class A finding (a cited US patent number that does not exist in the USPTO record) floors the entire draft's composite score to 0.0. Inequitable conduct is what *Therasense v. Becton Dickinson* (Fed. Cir. 2011) means by "fraud on the patent office" — fabricated prior-art is not a deduction, it is a kill-switch.

---

## v1.0 first public run

The v1.0 release will ship with a public run on three anonymized inventions (one mechanical, one medtech, one software). The disclosures are fully anonymized (inventor names, assignee names, specific numeric parameters redacted) and released under the same Apache-2.0 license as the rest of the repository.

Models evaluated in v1.0 (target):

- Claude Opus 4.7 · Sonnet 4.6 · Haiku 4.5
- GPT-5.4
- Llama 4 Maverick · Llama 3.3 70B
- DeepSeek R1
- Qwen 3 Max Thinking

Each model generates 3 independent drafts per invention (9 drafts per model, ~63 drafts total). Layers 1, 2, 4, 5A, 5B run automatically on all drafts; Layer 3 (blind expert review, Track B) runs on a stratified subset.

The full v1.0 INTA run is in flight. Run artifacts will be published under `data/v1.0-first-public-run/` once the run completes.

---

## Quick start

Install from source (pip package pending first release):

```bash
git clone https://github.com/cblindspot/draftbench
cd draftbench
pip install -e ".[dev]"
```

Set the OpenRouter key (single API key reaches Claude / GPT / Llama / DeepSeek / Qwen):

```bash
export OPENROUTER_API_KEY=sk-or-...
# Optional — enables Layer 5A Therasense USPTO verification via PatentsView.
# Without it, the harness falls back to Google Patents (HEAD probes, no auth).
export PATENTSVIEW_API_KEY=...
```

Run the mini example (1 invention, 4 frontier models, 1 repeat, ~$2 in compute):

```bash
draftbench run \
  --cases data/mini/cases.jsonl \
  --models claude-opus-4.7,claude-sonnet-4.6,gpt-5.4,llama-3.3-70b \
  --repeats 1 \
  --output-dir results/
```

Score the outputs through Layers 2, 4, 5A, 5B (LLM-judge for §112 US, jurisdictional EP/CN/JP, Therasense kill-switch, hallucination Classes B-E):

```bash
draftbench score results/run_<TIMESTAMP>.json \
  --output results/run_<TIMESTAMP>_scored.json \
  --judge-model claude-opus-4.7
```

Add `--cross-judge-model gpt-5.4` for cross-family bias control on Layer 2 (METHODOLOGY.md §10).

Generate a shareable HTML report (leaderboard, per-dimension breakdown, Pareto cost × quality, kill-switch findings):

```bash
draftbench report results/run_<TIMESTAMP>_scored.json \
  --output results/run_<TIMESTAMP>_report.html
```

Export blind-review packages for human reviewers (Layer 3, Track B):

```bash
draftbench export-blind results/run_<TIMESTAMP>.json \
  --output-dir results/blind_<TIMESTAMP>/ \
  --reviewers reviewer-a,reviewer-b,reviewer-c
```

List all available model IDs and their per-1M-token pricing:

```bash
draftbench list-models
```

Outputs land in `results/run_{timestamp}.{json,csv}` and the scored / report files alongside, with full model outputs, scoring breakdown, and raw API responses for reproducibility.

---

## Methodology

The full versioned methodology lives in [`METHODOLOGY.md`](./METHODOLOGY.md). Changes are tracked via SemVer — breaking changes bump the major version and are discussed in the issue tracker before merge.

DraftBench v1.0 follows four principles borrowed directly from [Artificial Analysis v4.0.4](https://artificialanalysis.ai/methodology/intelligence-benchmarking):

1. **Standardized** — identical prompts, temperature, token budgets across all models.
2. **Unbiased** — robust output extraction, flexible validation, no penalty for well-formed outputs that follow instructions differently.
3. **Zero-shot instruction prompted** — no few-shot examples in the drafting prompt.
4. **Transparent** — methodology, harness source, anonymized raw outputs all public.

---

## Roadmap

| Version | Target | Scope |
|---|---|---|
| **v1.0** | INTA 2026 (May) | Methodology published · harness released · first public run (7 LLMs × 3 inventions × 3 repeats) |
| v1.1 | August 2026 | Fleiss κ > 0.6 validated on 36 drafts · first Quarterly DraftBench Report |
| v1.2 | November 2026 | 5 vertical tools added (DeepIP, Solve, Patlytics, IP Author, Rowan) · 60-80 drafts · Track A integrated |
| v2.0 | April 2027 | 200+ drafts · 10+ tools · 10 stratified domains · academic journal submission |

---

## Contributing

We welcome contributions of:

- **Model adapters** — new LLM providers (see [`draftbench/models/`](./draftbench/models/))
- **Vendor tool adapters** — wrappers for commercial drafting tools with API access
- **Test inventions** — new anonymized disclosures, especially in under-represented domains (biotech, chemistry, AI/ML)
- **Rubrics** — refinements to the automatic metric rubrics in [`data/rubrics/`](./data/rubrics/)
- **Reviewers** — registered patent attorneys willing to join the blind-review panel

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full process. All contributions require a DCO sign-off and release under Apache-2.0.

---

## The ecosystem

DraftBench is part of an emerging open ecosystem of IP workflow benchmarks:

- [**PatentBench**](https://github.com/rhahn28/patentbench) — patent prosecution AI, 5 domains across the prosecution lifecycle *(Roger Hahn)*
- **DraftBench** — pre-filing patent drafting *(you are here)*
- **ValueBench** — patent valuation *(planned, H2 2026)*

Each benchmark is independently owned, open-sourced, and versioned. They share conventions (harness layout, result formats, contribution norms) but no code dependency.

---

## License

Apache License 2.0 — see [`LICENSE`](./LICENSE).

Apache-2.0 is chosen over MIT for a reason specific to this domain: Apache's patent grant clause provides a meaningful defense in a repository whose subject matter is itself patents. Contributors grant a license to any patent claims they own that their contribution practices.

---

## Citation

```bibtex
@misc{draftbench2026,
  title = {DraftBench v1.0: An Open Benchmark for AI-Assisted Patent Drafting},
  author = {CBlindspot},
  year = {2026},
  url = {https://github.com/cblindspot/draftbench}
}
```

---

## Acknowledgments

DraftBench was designed in dialogue with **Roger Hahn**, whose work on [PatentBench](https://github.com/rhahn28/patentbench) defined the template of an open IP workflow benchmark and whose feedback shaped the dual-track architecture.

---

*CBlindspot · cblindspot.ai*

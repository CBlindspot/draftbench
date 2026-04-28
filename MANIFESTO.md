# The DraftBench Manifesto

### Why Patent Drafting AI Has a Credibility Crisis, and How We Fix It

---

*"In God we trust. All others must bring data."*
W. Edwards Deming

---

## I. The Drafting Black Box

Patent drafting is the entry point of every patent's economic life. A claim that is too narrow is designed around in eighteen months. A claim that is too broad is invalidated in district court ten years later. A specification that fails §112(a) enablement is stripped of its entire scope at the PTAB. A drafting choice made in a Tuesday afternoon in 2026 can determine whether a portfolio worth eight figures survives or collapses in 2036.

Into this market, a new generation of AI companies has arrived. They have raised tens of millions of dollars. They promise to draft claims, specifications, and abstracts at a fraction of attorney time. They ask their customers — patent attorneys whose licenses are on the line — to trust them.

But here is the uncomfortable truth:

> **Not one of them publishes a reproducible benchmark proving their AI actually drafts patents that survive adversarial review.**

Not one.

---

## II. The Marketing-Claim Vacuum

Let us be specific, because specificity is what this corner of the industry lacks.

**DeepIP** advertises that it drafts "ready-to-file claims and specifications" trusted by enterprise IP teams. Where is the data? Where are the specifications evaluated against §112 conformance? Where are the claims compared to ground-truth patents that survived IPR? There are none. The published evidence is a feature comparison chart authored by DeepIP itself.

**Solve Intelligence** has raised significant venture capital and claims patent professionals are "50% more productive" with their tool. Productivity is a workflow metric. It tells you nothing about whether the drafted claims hold up at the PTAB, whether the specification supports them under §112(a), or whether the prior-art citations are real. Productivity gains on incorrect drafts are negative value.

**Patlytics**, **IP Author**, **Rowan Patents**, and the rest of the vertical drafting AI cohort all share the same pattern: marketing claims, customer testimonials, feature lists, internal benchmarks against undisclosed baselines. None has submitted to an independent, reproducible evaluation against a shared protocol.

This is not a criticism of any individual company. This is an indictment of an entire market segment that has decided **trust us** is an acceptable substitute for **here are the numbers** in a profession where bad drafts cause patent invalidity findings, malpractice claims, and inequitable conduct holdings.

---

## III. The Hallucination Problem in Drafting

In 2024, Stanford researchers measured hallucination rates in AI-powered legal research tools at 17% to 33% — fabricated citations, invented case holdings, hallucinated reasoning. The same underlying technology drafts patents.

In patent drafting, hallucination is not an academic concern. The inequitable-conduct doctrine, articulated by the Federal Circuit in *Therasense v. Becton Dickinson* (2011), holds that a single material misrepresentation of prior art — including a fabricated citation — can render an entire patent unenforceable. A drafting AI that confabulates a single prior-art reference into the specification or the IDS has, in that one act, created a kill-switch event that any motivated litigator will exploit ten years later.

The Therasense kill-switch is not negotiable. A drafting tool that fabricates prior art is not a tool that needs better fine-tuning. It is a tool that should be removed from production.

DraftBench tests for this directly. Class A hallucinations — fabricated prior-art citations — are an instant fail. Period.

---

## IV. The Benchmark Desert

Perhaps the benchmarks exist elsewhere? Perhaps academia has filled the gap?

No.

[**Artificial Analysis Intelligence Index v4.0.4**](https://artificialanalysis.ai/methodology/intelligence-benchmarking) is the most comprehensive public LLM evaluation suite. It covers ten evaluations across reasoning, knowledge, mathematics, coding, and agentic tasks. The number of those evaluations measuring patent drafting quality: **zero**.

[**LegalBench**](https://hazyresearch.stanford.edu/legalbench/) (2023) covers 162 legal tasks. Number addressing patent drafting: **zero**.

[**PatentBench**](https://github.com/rhahn28/patentbench) (Roger Hahn, 2026) is the first reproducible benchmark for patent prosecution AI, covering five domains across the prosecution lifecycle (Administration, Drafting, Prosecution, Analytics, Prior Art) — 7,200 test cases. PatentBench's Drafting domain focuses on post-filing claim amendment in Office Action response. Pre-filing drafting (invention disclosure → claims → specification → abstract) is the gap DraftBench fills.

This is the state of the field: a multi-billion-dollar drafting AI segment with **zero published, reproducible benchmarks** evaluating the quality of generated claims, specifications, and abstracts under a shared protocol.

> **You cannot improve what you cannot measure. Right now, the patent drafting AI industry refuses to measure.**

---

## V. What DraftBench Is

DraftBench is the benchmark this industry should have built two years ago, and didn't.

### The Architecture

- **Dual-track scoring** — 60% historical durability (Track A: claims reverse-engineered from patents that survived PTAB IPR, EPO opposition, reexamination, district court validity challenges) + 40% expert blind review (Track B: registered patent attorneys, blind-rated)
- **Seven weighted dimensions** — Claim Drafting Quality (35%), Specification Quality (20%), Prosecution & Post-Grant Durability (15%), Workflow & UX (10%), AI Safety & Fabrication Resistance (10%), Confidentiality / Privilege / Trust (5%), Integration & TCO (5%)
- **Five-layer harness** — structural (MPEP 608.01 + claim format) → §112 US LLM-judge → human panel reserved → jurisdictional (EP/CN/JP) LLM-judge → hallucination 5-class taxonomy + Therasense kill-switch
- **Therasense kill-switch** — fabricated prior-art citations are an instant fail. Not a deduction. Not a penalty. An instant fail.

### What Makes It Different

**Outcome-based evaluation.** Track A's reference corpus is built from patents that survived adversarial review in the real world. The "correct" claims are the ones that held up. Model-generated claims are scored against ground truth that has already been tested by motivated adversaries.

**Anti-fabrication first.** Every cited prior-art reference is verified against USPTO Patent Public Search. A drafting tool that survives DraftBench did not invent its citations.

**Cross-family LLM judging.** When LLM-as-judge is used (Layers 2, 4, 5), Claude judges GPT outputs and vice versa. Family bias is controlled by construction, not by trust.

**Versioned methodology.** SemVer applied. Breaking changes require sixty-day public comment + academic partner sign-off. Historical runs remain reproducible against the methodology version they were executed under.

---

## VI. The Glass Box Standard

DraftBench is built on five pillars of transparency we call the **Glass Box Standard**:

> **1. Open methodology.** Every rubric, every weighting decision, every scoring threshold is published. There are no proprietary secret sauces in how we grade.
>
> **2. Reproducible results.** Any team with access to the test set can run the benchmark independently and verify our numbers. If you disagree with a score, you can prove it.
>
> **3. Real data provenance.** Every test case in Track A traces back to a specific USPTO patent number with a specific survival event (PTAB IPR final written decision, EPO opposition decision, district court validity ruling).
>
> **4. Version-controlled evolution.** As patent law evolves, so does DraftBench. Every change is versioned, documented, and justified. Historical results remain comparable.
>
> **5. Conflict-free evaluation.** No vendor grades itself. The benchmark exists independently of any commercial product, including any product CBlindspot itself ships.

We adopt Glass Box because that is exactly what the patent drafting industry needs: not a black box that asks for trust, but a transparent system that earns it.

---

## VII. Why CBlindspot Is Doing This

A reasonable question: why would a CBlindspot — a company building a vendor-evaluation platform for IP technology — publish an open standard that any of its evaluated vendors can adopt and ship under their own brand?

The answer is straightforward.

**Defining the standard is the highest-leverage contribution we can make.** [SWE-bench](https://www.swebench.com/) did not just measure coding agents — it defined what *good* means for automated software engineering. Every coding-AI company now reports SWE-bench scores. PatentBench is doing the same for prosecution. DraftBench fills the drafting gap. The entity that defines how the world evaluates patent drafting AI shapes the entire market's direction.

**A vendor-graded benchmark is structurally compromised.** A vendor that publishes its own benchmark is structurally accused of "benchmaxxing". A vendor that publishes a versioned, open methodology, with an independent reference harness, that any third party can execute, has a different defensibility profile. We take that playbook.

**Trust is earned through evidence, not asked through marketing.** CBlindspot's product depends on the credibility of vendor evaluations. The credibility of vendor evaluations depends on the methodology being public, reproducible, and unbiased. DraftBench is the foundation, not a side project.

We are not doing this despite running a vendor platform. We are doing this *because* we run a vendor platform — one that believes the IP market is better when customers can make procurement decisions based on real data.

---

## VIII. The Challenge

This section is addressed directly to every company building AI for patent drafting.

To **DeepIP**: You publish feature comparison charts authored by your own team. Replace them with something the market can trust. Submit your tool for DraftBench evaluation.

To **Solve Intelligence**: You claim 50% productivity gains. Productivity on what? Drafts that hold up at the PTAB, or drafts that look fluent? Submit your tool. Let the data answer.

To **Patlytics**, **IP Author**, **Rowan Patents**, **Ankar**, and every other vertical drafting AI: Your customers — registered patent attorneys whose licenses depend on the integrity of the drafts they sign — deserve standardized, independently verified evaluation. Submit your tool.

To **every drafting AI startup, every legal tech platform, every LLM wrapper with a "draft a patent" button**: the era of "trust us" is ending. The era of "show us" begins now.

> **If your product drafts better, show the numbers.**
>
> **If your AI does not fabricate prior art, prove it.**
>
> **If you will not submit to independent evaluation, ask yourself why, and know that your customers will ask the same question.**

---

## IX. A Note on What We Owe

Patent attorneys are fiduciaries. They owe a duty of candor to the USPTO under 37 CFR 1.56 and a duty of competence to their clients under their state bar rules. When an attorney signs a draft generated by an AI tool, that tool becomes part of the attorney's professional obligation. The attorney is staking their license on the tool's output.

Those attorneys deserve to know, with data — not marketing — how reliable that output is. They deserve benchmarks built by practitioners who understand what competent drafting looks like. They deserve transparency.

The Stanford hallucination study proved that even nine-figure acquisitions can produce legal-AI tools that fabricate one in six responses. In a profession where a single fabrication can constitute fraud on the USPTO under *Therasense*, "pretty good most of the time" is not a standard. It is a liability.

DraftBench exists because the patent drafting profession deserves better than trust. It deserves proof.

---

## X. Join Us

DraftBench is not a product. It is an open standard for an industry that has operated without one.

If you are a **patent attorney** frustrated by drafting-tool claims you cannot verify: ask every vendor in your procurement process the same question. *What is your DraftBench score?*

If you are a **drafting AI company** confident in your product: submit it for evaluation. The best marketing in the world is an independently verified top score.

If you are a **researcher** working on legal AI: build on DraftBench. Extend it. Challenge it. Make it better. That is what open standards are for.

If you are an **investor** evaluating drafting AI companies: demand benchmark data before writing checks. The drafting segment has consumed tens of millions in venture capital without producing a single reproducible drafting-quality metric. That should concern you.

The benchmark exists. The methodology is published. The harness is open-source.

**The only question left is who is willing to be measured.**

---

<p align="center"><em>DraftBench is a project of CBlindspot — a vertical deep-dive on pre-filing patent drafting, complementary to <a href="https://github.com/rhahn28/patentbench">PatentBench</a>'s horizontal coverage of patent prosecution AI in an open ecosystem of IP-workflow benchmarks.</em></p>

<p align="center"><strong>cblindspot.ai</strong> | <strong>github.com/cblindspot/draftbench</strong></p>

<p align="center"><em>"You cannot improve what you cannot measure."</em></p>

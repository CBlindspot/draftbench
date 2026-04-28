# DraftBench Mini Test Set

Three synthetic, public-domain invention disclosures for fast harness validation.

| ID | Domain | Tier | Provenance |
|---|---|:---:|---|
| `public_widget_clamp` | mechanical | 2 | `synthetic_public_domain` |
| `public_neural_stim` | medtech | 4 | `synthetic_public_domain` |
| `public_citation_rag` | software | 3 | `synthetic_public_domain` |

## What "synthetic public-domain" means

These disclosures are written from scratch for benchmark validation purposes. They are not derived from any specific filed application and do not reproduce confidential client work product. Inventive-element lists, embodiment details, and prior-art citations are illustrative — fabricated US patent numbers in the prior-art context (`US 9,123,456`, `US 11,234,567`, etc.) are present *intentionally* as part of the AI Safety / Fabrication Resistance test (Dim 5, METHODOLOGY.md §4.1, Class A — Therasense kill-switch verification).

## Typical run

```bash
draftbench run \
    --cases data/mini/cases.jsonl \
    --models claude-opus-4.7,claude-sonnet-4.6,gpt-5.4,llama-3.3-70b \
    --repeats 1
```

Approximate compute cost: ~$2 for one repeat across the four frontier models.

## Schema

Each line of `cases.jsonl` is one record with fields:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `id` | string | ✓ | Snake-case unique identifier |
| `title` | string | ✓ | Title of the invention |
| `domain` | string | ✓ | One of: mechanical, medtech, software, chemistry, biotech, semiconductor, materials, ai_ml, communications, energy |
| `tier` | int (1-5) | — | Difficulty tier per METHODOLOGY.md §9 |
| `provenance` | string | — | `synthetic_public_domain` \| `reverse_engineered_uspto` \| `pilot_partner_anonymized` |
| `background` | string | ✓ | Field of invention + problem statement |
| `inventive_elements` | string[] | ✓ | List of distinguishing technical elements |
| `embodiments` | string | ✓ | Implementation details |
| `prior_art_summary` | string | — | Optional context describing references the disclosure must distinguish over |

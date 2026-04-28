# Contributing to DraftBench

Thank you for your interest in contributing. DraftBench is an open standard — its credibility depends on broad community contribution. This document covers how to contribute test inventions, evaluation rubrics, model and vendor adapters, and core framework improvements.

## How to Contribute

### Contributing Test Inventions

Test inventions are the foundation of DraftBench. We welcome high-quality, expert-curated disclosures that broaden domain coverage.

#### Requirements

1. **Real provenance.** Track A inventions must derive from a specific USPTO patent with a qualifying survival event (PTAB IPR final written decision, EPO opposition decision, reexamination outcome, commercial validation, or expert-panel-drafted reference). Synthetic inventions are accepted for v1.1+ contamination-control purposes.
2. **Anonymization pass.** Inventor names, assignee names, exact numerical parameters, and any identifier that ties the disclosure to a single product or company must be redacted. The disclosure must not be searchable to a single source.
3. **Expert validation.** Each contributed invention must be reviewed by a registered patent attorney before merge. Include attorney name and registration number in the PR description (publication is at attorney's discretion).
4. **Domain tagging.** Tag the invention with one of the canonical domains: mechanical, medtech, software, chemistry, biotech, semiconductor, materials, AI/ML, communications, energy.
5. **Complete metadata.** Application number (where applicable), survival event type, technology area, complexity tier (1-5), filing date.

#### Process

1. Fork the repository.
2. Create the invention file in JSONL format under `data/full/<domain>/`.
3. Validate: `draftbench validate-invention path/to/file.jsonl`.
4. Submit a PR with:
   - The invention file
   - A description of the technology area, survival event, and difficulty tier
   - Confirmation of expert review (attorney name, registration number, signed-off date)

### Contributing Evaluation Rubrics

Rubrics define the scoring criteria for the seven dimensions in both Track A and Track B. They live in `data/rubrics/dim{N}_{slug}.json`.

#### Requirements

1. Follow the rubric JSON schema in `data/rubrics/README.md`.
2. Include detailed criteria for each score level (1-5) with at least one anchor example per level.
3. Validate the rubric against at least 10 sample drafts before submission.
4. Include reviewer-calibration notes — what the rubric is *not* trying to measure, to prevent scope creep.

### Contributing Model Adapters

Model adapters connect a new LLM provider, a commercial drafting tool, or an internal system to the benchmark harness.

#### Requirements

1. Extend `BaseModelAdapter` from `draftbench/models/base.py`.
2. Implement `generate(prompt: str, config: GenerationConfig | None) -> str` and `is_available() -> bool`.
3. Handle authentication via environment variables or constructor parameters. Never commit API keys.
4. Include error handling, exponential backoff (matching the methodology §7 retry policy), and timeout logic.
5. Register the adapter in `draftbench/models/__init__.py`.
6. Add unit tests in `tests/`.

#### Example

```python
from draftbench.models.base import BaseModelAdapter, GenerationConfig

class MyDraftingToolAdapter(BaseModelAdapter):
    model_name = "my-drafting-tool-v1"

    def __init__(self, api_key: str | None = None):
        super().__init__(model_name=self.model_name)
        self.api_key = api_key or os.environ.get("MY_TOOL_API_KEY", "")

    def generate(self, prompt: str, config: GenerationConfig | None = None) -> str:
        # Translate the drafting prompt to the tool's native API and render
        # the structured output (claims + spec + abstract) as text.
        ...

    def is_available(self) -> bool:
        return bool(self.api_key)
```

For commercial drafting tools without API access (e.g., UI-only platforms), see [INTEGRATION.md](INTEGRATION.md) for CSV round-trip and browser-automation patterns.

## Development Setup

```bash
git clone https://github.com/cblindspot/draftbench
cd draftbench
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest -v
pytest --cov=draftbench
```

## Code Style

- Python 3.10+ with type hints on all public function signatures.
- `ruff` for linting: `ruff check .`
- `mypy` for type checking: `mypy draftbench/`
- Dataclasses and enums over plain dicts/strings where appropriate.
- Docstrings on all public classes and functions.

## Pull Request Process

1. Create a feature branch from `main`.
2. Write tests for new functionality.
3. Ensure all tests pass and linting is clean.
4. Update `METHODOLOGY.md` if your change affects scoring semantics — methodology changes require a SemVer bump per §13.
5. Submit a PR with a clear description of changes and (for methodology-affecting changes) a justification keyed to a specific limitation in the existing methodology.

## Reporting Issues

Use GitHub Issues for:
- Bug reports (include reproduction steps and the methodology version)
- Feature requests
- Test invention quality concerns
- Documentation improvements
- Open-question resolutions (per METHODOLOGY.md §16)

## Methodology Change Process

DraftBench follows SemVer. Methodology changes are categorized:

- **PATCH** (v1.0.0 → v1.0.1) — rubric text clarifications, prompt wording fixes, typos. Maintainer-merged.
- **MINOR** (v1.0 → v1.1) — new corpus additions, new model adapters, new sub-criteria. Backward-compatible. Reviewed by at least two maintainers.
- **MAJOR** (v1 → v2) — breaking changes to dimension structure, weightings, or Track A/B definition. Requires sixty-day public comment period + academic partner sign-off.

## Code of Conduct

Be respectful, constructive, and collaborative. We are building shared infrastructure for the patent profession.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0. Apache-2.0 is chosen over MIT for a reason specific to this domain: the patent grant clause provides a meaningful defense in a repository whose subject matter is itself patents.

Copyright 2026 CBlindspot.

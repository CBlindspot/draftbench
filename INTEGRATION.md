# Integrating Drafting Systems with DraftBench

This guide explains how to evaluate any patent drafting AI system on DraftBench, whether it is:

- **A direct-API LLM** (OpenRouter, OpenAI, Anthropic, Google) — already supported
- **A commercial drafting tool** (DeepIP, Solve Intelligence, Patlytics, IP Author, Rowan Patents) — supported via custom adapters
- **A web-only tool with no API** — supported via CSV round-trip or browser automation
- **A proprietary internal system** — supported via any of the above

Every evaluation path produces the same `results/run_<timestamp>/` artifact tree, so results are directly comparable regardless of how the system was accessed.

---

## Contents

1. [Core Architecture: The Adapter Pattern](#core-architecture-the-adapter-pattern)
2. [What the Evaluator Reads](#what-the-evaluator-reads)
3. [Pattern 1: Direct API Integration](#pattern-1-direct-api-integration)
4. [Pattern 2: CSV Round-Trip (No-API Option)](#pattern-2-csv-round-trip-no-api-option)
5. [Pattern 3: Browser Automation (UI-Only Tools)](#pattern-3-browser-automation-ui-only-tools)
6. [Submitting Results to the Leaderboard](#submitting-results-to-the-leaderboard)

---

## Core Architecture: The Adapter Pattern

DraftBench's harness does not care how a draft is produced. It cares about the text that comes back. Every "model" conforms to one interface:

```python
class BaseModelAdapter:
    def generate(self, prompt: str, config: GenerationConfig | None = None) -> str:
        """Take a drafting prompt. Return claims + specification + abstract as text."""

    def is_available(self) -> bool:
        """Return True if the system is reachable and authenticated."""
```

That is the entire contract. The `generate()` method can:

- Call a REST API
- Drive a browser with Playwright
- Look up a cached response from a CSV
- Shell out to a CLI tool
- Read from a human-entered text file

As long as it returns text containing the drafted output, the harness can score it.

---

## What the Evaluator Reads

A DraftBench draft is expected to contain three sections, in order:

1. **Independent + dependent claims** — numbered, MPEP 608.01 format
2. **Specification** — Field of Invention, Background, Summary, Detailed Description, Brief Description of Drawings (where applicable)
3. **Abstract** — ≤150 words, MPEP 608.01(b) format

The auto-scoring harness (Layers 1-2-4-5 of §6 in METHODOLOGY.md) parses these sections out of the returned text using lenient regex + section-header detection. Your adapter does *not* need to produce a specific JSON shape — it needs to produce a text response that contains the three sections in identifiable form.

If your adapter returns sections in a non-standard order or with non-standard headers, override `BaseModelAdapter.parse_sections()` to expose the section structure to the harness directly.

---

## Pattern 1: Direct API Integration

Use this when the system has any kind of network-accessible API.

### 1.1 Built-in Adapters

Already supported:

```bash
draftbench run --models openrouter:anthropic/claude-opus-4.7 --cases data/mini/cases.jsonl
draftbench run --models openrouter:openai/gpt-5.4 --cases data/mini/cases.jsonl
draftbench run --models openrouter:meta-llama/llama-3.3-70b-instruct --cases data/mini/cases.jsonl
```

OpenRouter is the recommended path for v1.0 — single API key, unified pricing, broad model coverage including Claude Opus/Sonnet/Haiku, GPT-5.4, Llama 3.3, Deepseek R1/V3.2, and Qwen 3.6.

### 1.2 Writing a Custom Adapter

Create `draftbench/models/your_adapter.py`:

```python
"""Adapter for <your drafting tool>."""

from __future__ import annotations
import os
import httpx
from draftbench.models.base import BaseModelAdapter, GenerationConfig


class YourToolAdapter(BaseModelAdapter):
    """Adapter for <Your Drafting Tool>.

    Translates DraftBench drafting prompts into the tool's native
    API schema and converts the structured response back to text
    containing the three required sections (claims, spec, abstract).
    """

    model_name = "your-tool-v1"

    def __init__(self, api_key: str | None = None, endpoint: str | None = None):
        super().__init__(model_name=self.model_name)
        self.api_key = api_key or os.environ.get("YOUR_TOOL_API_KEY", "")
        self.endpoint = endpoint or "https://api.yourtool.com"

    def generate(self, prompt: str, config: GenerationConfig | None = None) -> str:
        # Step 1: Translate prompt into the tool's invention-disclosure schema
        payload = self._render_disclosure_payload(prompt)

        # Step 2: Call the tool's drafting endpoint
        response = httpx.post(
            f"{self.endpoint}/v1/draft",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=300,  # drafting can take several minutes
        )
        response.raise_for_status()
        data = response.json()

        # Step 3: Render the structured response back to text containing
        # claims + specification + abstract in identifiable sections.
        return self._render_draft(data)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _render_disclosure_payload(self, prompt: str) -> dict:
        # Parse the DraftBench prompt (Field of Invention + Background + Summary
        # of the disclosure) and structure it for the tool's API.
        ...

    def _render_draft(self, data: dict) -> str:
        # Concatenate claims, spec, and abstract into a single text response
        # with section headers the harness can detect.
        sections = [
            "## Claims",
            "\n\n".join(data["claims"]),
            "## Specification",
            data["specification"],
            "## Abstract",
            data["abstract"],
        ]
        return "\n\n".join(sections)
```

### 1.3 Register and Use

Add to `draftbench/models/__init__.py`:

```python
from draftbench.models.your_adapter import YourToolAdapter
```

Run programmatically:

```python
from draftbench import BenchmarkRunner, BenchmarkConfig
from draftbench.data_loader import DataLoader
from draftbench.models.your_adapter import YourToolAdapter

model = YourToolAdapter(api_key="...")
cases = DataLoader("data/mini").load_all()
config = BenchmarkConfig(repeats=3, max_output_tokens=16384)
runner = BenchmarkRunner(model=model, cases=cases, config=config)
results = runner.run()
results.save("results/your_tool_mini.json")
```

Or expose it through the CLI by adding a dispatcher entry in `draftbench/__main__.py`.

---

## Pattern 2: CSV Round-Trip (No-API Option)

Use this when:

- The tool has no API at all
- You need manual human-in-the-loop drafting
- You want to evaluate a system you have limited access to
- You are running a pilot before investing in automation

### 2.1 Export Drafting Prompts

```bash
draftbench export-prompts --cases data/mini/cases.jsonl --output prompts_to_run.csv
```

This produces a CSV with one row per (invention, repeat) and an empty `response` column.

### 2.2 Fill the CSV

A human operator runs each prompt through the target tool's UI and pastes the resulting draft into the `response` column. Multiple operators can parallelize across rows.

### 2.3 Score the Filled CSV

```bash
draftbench score-csv responses_from_tool.csv --model your-tool-name --output results/run_csv_<timestamp>.json
```

The output matches the format produced by API-based runs and can be submitted to the leaderboard alongside automated runs.

---

## Pattern 3: Browser Automation (UI-Only Tools)

Use this when the tool has no API but you want full automation instead of manual CSV work.

Requires Playwright: `pip install playwright && playwright install chromium`.

```python
from playwright.sync_api import sync_playwright
from draftbench.models.base import BaseModelAdapter, GenerationConfig


class BrowserDrivenAdapter(BaseModelAdapter):
    """Drive a web UI to produce drafts.

    This is the most fragile integration. It depends on the target
    site's HTML structure. Expect to update selectors periodically.
    """

    model_name = "browser-driven-tool"

    def __init__(self, url: str, username: str, password: str, headless: bool = True):
        super().__init__(model_name=self.model_name)
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        self._page = self._browser.new_page()

        self._page.goto(f"{url}/login")
        self._page.fill("input[name='email']", username)
        self._page.fill("input[name='password']", password)
        self._page.click("button[type='submit']")
        self._page.wait_for_url("**/dashboard", timeout=30000)
        self._draft_url = f"{url}/draft"

    def generate(self, prompt: str, config: GenerationConfig | None = None) -> str:
        self._page.goto(self._draft_url)
        self._page.fill("textarea[name='disclosure']", prompt)
        self._page.click("button#draft")
        # Drafting can take minutes — wait generously
        self._page.wait_for_selector(".draft-output", timeout=600000)
        return self._page.inner_text(".draft-output")

    def is_available(self) -> bool:
        try:
            self._page.goto(self._draft_url, timeout=10000)
            return True
        except Exception:
            return False

    def __del__(self):
        try:
            self._browser.close()
            self._pw.stop()
        except Exception:
            pass
```

### Tips for Browser Automation

- **Rate-limit**: add `time.sleep(2-5)` between drafts to avoid anti-bot protections.
- **Respect Terms of Service**: verify that benchmarking via automation is permitted.
- **Session expiry**: add re-login logic on long runs (drafting 36 inventions can take hours).
- **Screenshot on failure**: `self._page.screenshot(path="error.png")` for debugging.
- **Captchas**: if the tool shows captchas, browser automation is not viable — fall back to CSV pattern.

---

## Submitting Results to the Leaderboard

Once you have a `results/run_<timestamp>/` directory:

1. **Verify the result tree is complete** — `summary.csv`, `composite.csv`, per-(invention, model, repeat) JSON files, blind-review export.
2. **Run the full `mini` set** at minimum (1 invention × at least 4 frontier models × 3 repeats). Partial runs are not directly comparable.
3. **Document your methodology**:
   - System version tested
   - Adapter pattern used (API / CSV / browser)
   - Configuration (temperature, max tokens, retries, model variant)
   - Date range of the evaluation
4. **Open a pull request** adding your results:
   - Result directory under `reports/<your-system>_<YYYY-MM-DD>/`
   - Leaderboard table entry in `README.md`
   - Methodology note in the PR description
5. **For full reproducibility**:
   - API-based: share adapter source code (minus credentials)
   - CSV-based: share filled CSVs so scores can be recomputed
   - Browser-based: share selector config and target site version

---

## FAQ

### My tool only handles claim generation, not full specifications. Can I still benchmark?

Yes, with reduced scope. Run only the claim-generation slice:

```bash
draftbench run --models your-tool --cases data/mini/cases.jsonl --output-types claims-only
```

Your composite score will be capped (Dim 2 Specification Quality contributes 20% of the composite). Document the scope in your leaderboard submission.

### My tool returns a Word document, not text. How do I score it?

Your adapter's `generate()` should extract text from the document. Use `python-docx`:

```python
import docx
from io import BytesIO

def generate(self, prompt: str, config=None) -> str:
    docx_bytes = self._call_tool(prompt)
    doc = docx.Document(BytesIO(docx_bytes))
    return "\n\n".join(p.text for p in doc.paragraphs)
```

### Does DraftBench prevent test-set leakage?

Partial. v1.0 includes synthetic and post-2024 inventions specifically chosen to be outside likely training cutoffs. Track A reverse-engineered inventions are anonymized, but the underlying USPTO patents are public — leakage is a known threat (METHODOLOGY.md §11). v1.1 introduces a contamination-canary protocol.

### Can I evaluate on cached / pre-computed responses?

Yes. Write an adapter that reads from a local cache:

```python
class CachedResponseAdapter(BaseModelAdapter):
    model_name = "cached"

    def __init__(self, cache_file: str):
        import json
        with open(cache_file) as f:
            self.cache = json.load(f)

    def generate(self, prompt: str, config=None) -> str:
        import hashlib
        key = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return self.cache.get(key, "")

    def is_available(self) -> bool:
        return bool(self.cache)
```

Useful for re-scoring runs with updated rubrics without re-calling expensive APIs.

---

## Need Help?

- **Adapter not working?** File an issue at https://github.com/cblindspot/draftbench/issues with your adapter code and the error.
- **Schema questions?** See [METHODOLOGY.md](METHODOLOGY.md) §6 (harness layers) and §12 (reporting format).
- **Leaderboard submission?** See [CONTRIBUTING.md](CONTRIBUTING.md).

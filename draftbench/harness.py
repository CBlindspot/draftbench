"""Benchmark orchestration — runs N adapters × M inventions × K repeats."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from draftbench.config import BenchmarkConfig
from draftbench.metrics import summarize_auto_metrics
from draftbench.models.base import BaseModelAdapter, GenerationConfig
from draftbench.prompts import DRAFTING_SYSTEM_PROMPT, build_user_prompt


@dataclass
class BenchmarkResults:
    """All drafts + metadata produced by a single `BenchmarkRunner.run()` invocation."""

    run_id: str
    started_at: str
    finished_at: str
    config: dict[str, Any]
    model_names: list[str]
    invention_ids: list[str]
    drafts: list[dict] = field(default_factory=list)

    # ------------------------------------------------------------------------ I/O

    def save(self, path: str | Path) -> Path:
        """Write the full results bundle as a single JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))
        return p

    def save_summary_csv(self, path: str | Path) -> Path:
        """One row per draft with auto-metrics flattened — useful for spreadsheets."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "model_name", "invention_id", "invention_title", "repeat",
            "succeeded", "error", "latency_ms",
            "tokens_in", "tokens_out", "cost_usd",
            "claims_total", "claims_independent", "claims_dependent",
            "abstract_word_count", "abstract_within_150w",
            "has_abstract", "has_claims", "has_specification",
            "output_char_count", "output_word_count",
        ]
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for d in self.drafts:
                am = d.get("auto_metrics", {}) or {}
                claims = am.get("claims", {}) or {}
                w.writerow(
                    {
                        "model_name": d["model_name"],
                        "invention_id": d["invention_id"],
                        "invention_title": d.get("invention_title", ""),
                        "repeat": d.get("repeat", 0),
                        "succeeded": d["succeeded"],
                        "error": d.get("error") or "",
                        "latency_ms": d["latency_ms"],
                        "tokens_in": d["tokens_in"],
                        "tokens_out": d["tokens_out"],
                        "cost_usd": d["cost_usd"],
                        "claims_total": claims.get("total", 0),
                        "claims_independent": claims.get("independent", 0),
                        "claims_dependent": claims.get("dependent", 0),
                        "abstract_word_count": am.get("abstract_word_count", 0),
                        "abstract_within_150w": am.get("abstract_within_150w", False),
                        "has_abstract": am.get("has_abstract", False),
                        "has_claims": am.get("has_claims", False),
                        "has_specification": am.get("has_specification", False),
                        "output_char_count": am.get("output_char_count", 0),
                        "output_word_count": am.get("output_word_count", 0),
                    }
                )
        return p

    def summary(self) -> str:
        """Human-readable one-line summary."""
        n = len(self.drafts)
        succeeded = sum(1 for d in self.drafts if d["succeeded"])
        cost = sum(d["cost_usd"] for d in self.drafts)
        return f"{succeeded}/{n} succeeded · ${cost:.4f} total cost · {self.run_id}"


class BenchmarkRunner:
    """Runs each adapter on each invention `repeats` times, collects drafts + auto-metrics."""

    def __init__(
        self,
        adapters: list[BaseModelAdapter],
        inventions: list[dict],
        config: BenchmarkConfig | None = None,
        system_prompt: str = DRAFTING_SYSTEM_PROMPT,
    ):
        self.adapters = adapters
        self.inventions = inventions
        self.config = config or BenchmarkConfig()
        self.system_prompt = system_prompt

    def run(self) -> BenchmarkResults:
        started = datetime.now(timezone.utc)
        run_id = f"run_{started.strftime('%Y%m%d-%H%M%S')}"
        gen_config = GenerationConfig(
            max_output_tokens=self.config.max_output_tokens,
            temperature=self.config.temperature,
        )

        drafts: list[dict] = []
        for inv in self.inventions:
            inv_id = inv["id"]
            user_prompt = build_user_prompt(inv)
            for adapter in self.adapters:
                for repeat in range(1, self.config.repeats + 1):
                    print(
                        f"  [{adapter.model_name}] {inv_id} repeat {repeat}/{self.config.repeats}…",
                        flush=True,
                    )
                    result = adapter.draft(
                        invention_id=inv_id,
                        system=self.system_prompt,
                        user=user_prompt,
                        config=gen_config,
                        retries=self.config.retries,
                    )
                    metrics = summarize_auto_metrics(result.output_text) if result.succeeded else {}
                    drafts.append(
                        {
                            "model_name": result.model_name,
                            "invention_id": result.invention_id,
                            "invention_title": inv.get("title", ""),
                            "repeat": repeat,
                            "succeeded": result.succeeded,
                            "error": result.error,
                            "latency_ms": result.latency_ms,
                            "tokens_in": result.tokens_in,
                            "tokens_out": result.tokens_out,
                            "cost_usd": result.cost_usd,
                            "auto_metrics": metrics,
                            "output_text": result.output_text,
                            "raw_response": result.raw_response,
                        }
                    )

        finished = datetime.now(timezone.utc)
        return BenchmarkResults(
            run_id=run_id,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            config=asdict(self.config),
            model_names=[a.model_name for a in self.adapters],
            invention_ids=[inv["id"] for inv in self.inventions],
            drafts=drafts,
        )

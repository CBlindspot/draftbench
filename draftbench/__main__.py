"""DraftBench CLI entry point — `draftbench {run,score,export-blind,report}`.

v1.0 wires `run` end-to-end. `score`, `export-blind`, and `report` have
scaffolded subcommands that delegate to in-progress modules; full
implementations land per IMPLEMENTATION_CHECKLIST.md Phase 2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from draftbench import __version__
from draftbench.blind_review import write_blind_review_package
from draftbench.config import BenchmarkConfig
from draftbench.data_loader import DataLoader
from draftbench.harness import BenchmarkRunner

# Hardcoded model registry — keep stable for reproducibility. Refresh via
# `python -m scripts.refresh_pricing`.
MODEL_REGISTRY: dict[str, dict] = {
    "claude-opus-4.7":     {"openrouter_id": "anthropic/claude-opus-4.7",     "in": 5.0,   "out": 25.0},
    "claude-sonnet-4.6":   {"openrouter_id": "anthropic/claude-sonnet-4.6",   "in": 3.0,   "out": 15.0},
    "claude-haiku-4.5":    {"openrouter_id": "anthropic/claude-haiku-4.5",    "in": 1.0,   "out": 5.0},
    "gpt-5.4":             {"openrouter_id": "openai/gpt-5.4",                "in": 2.5,   "out": 15.0},
    "gpt-5.4-pro":         {"openrouter_id": "openai/gpt-5.4-pro",            "in": 30.0,  "out": 180.0},
    "llama-4-maverick":    {"openrouter_id": "meta-llama/llama-4-maverick",   "in": 0.15,  "out": 0.60},
    "llama-3.3-70b":       {"openrouter_id": "meta-llama/llama-3.3-70b-instruct", "in": 0.12, "out": 0.38},
    "hermes-3-llama-405b": {"openrouter_id": "nousresearch/hermes-3-llama-3.1-405b", "in": 1.0, "out": 1.0},
    "deepseek-r1":         {"openrouter_id": "deepseek/deepseek-r1-0528",     "in": 0.5,   "out": 2.15},
    "deepseek-v3.2":       {"openrouter_id": "deepseek/deepseek-v3.2",        "in": 0.252, "out": 0.378},
    "qwen3-max-thinking":  {"openrouter_id": "qwen/qwen3-max-thinking",       "in": 0.78,  "out": 3.90},
    "qwen3.6-plus":        {"openrouter_id": "qwen/qwen3.6-plus",             "in": 0.325, "out": 1.95},
}


@click.group()
@click.version_option(__version__, prog_name="draftbench")
def cli() -> None:
    """DraftBench — open benchmark for AI-assisted patent drafting."""


@cli.command()
@click.option("--cases", type=click.Path(exists=True, dir_okay=False), required=True,
              help="JSONL file of invention test cases.")
@click.option("--models", required=True,
              help="Comma-separated model IDs (see `draftbench list-models`), or 'all'.")
@click.option("--repeats", type=int, default=3, show_default=True,
              help="Repeats per (model, invention).")
@click.option("--max-output-tokens", type=int, default=16384, show_default=True)
@click.option("--output-dir", type=click.Path(file_okay=False), default="./results", show_default=True)
def run(cases: str, models: str, repeats: int, max_output_tokens: int, output_dir: str) -> None:
    """Run the benchmark — generate drafts across (models × cases × repeats)."""
    from draftbench.models import OpenRouterAdapter

    if models == "all":
        model_ids = list(MODEL_REGISTRY.keys())
    else:
        model_ids = [m.strip() for m in models.split(",") if m.strip()]

    unknown = [m for m in model_ids if m not in MODEL_REGISTRY]
    if unknown:
        click.echo(f"Unknown models: {unknown}. Run `draftbench list-models`.", err=True)
        sys.exit(1)

    adapters = []
    for mid in model_ids:
        cfg = MODEL_REGISTRY[mid]
        adapters.append(OpenRouterAdapter(
            model=cfg["openrouter_id"],
            pricing_in=cfg["in"],
            pricing_out=cfg["out"],
            display_name=mid,
        ))

    inventions = DataLoader(Path(cases).parent).load_file(cases)
    config = BenchmarkConfig(repeats=repeats, max_output_tokens=max_output_tokens)
    runner = BenchmarkRunner(adapters=adapters, inventions=inventions, config=config)
    click.echo(f"Running: {len(adapters)} models × {len(inventions)} inventions × {repeats} repeats")
    results = runner.run()

    out = Path(output_dir)
    json_path = out / f"{results.run_id}.json"
    csv_path = out / f"{results.run_id}.csv"
    results.save(json_path)
    results.save_summary_csv(csv_path)

    click.echo(f"\n{results.summary()}")
    click.echo(f"  JSON:    {json_path}")
    click.echo(f"  CSV:     {csv_path}")


@cli.command(name="list-models")
def list_models() -> None:
    """List available model IDs and their pricing (USD per 1M tokens)."""
    click.echo(f"{'ID':24s}  {'OpenRouter model':50s}  {'$/1M in':>10s}  {'$/1M out':>10s}")
    for mid, cfg in MODEL_REGISTRY.items():
        click.echo(f"{mid:24s}  {cfg['openrouter_id']:50s}  {cfg['in']:>10.3f}  {cfg['out']:>10.3f}")


@cli.command(name="export-blind")
@click.argument("results_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--reviewers", default="reviewer_a,reviewer_b,reviewer_c", show_default=True,
              help="Comma-separated reviewer IDs — one folder per reviewer.")
@click.option("--output-dir", type=click.Path(file_okay=False), required=True)
def export_blind(results_path: str, reviewers: str, output_dir: str) -> None:
    """Export blind-review packages from a results JSON for the human panel."""
    payload = json.loads(Path(results_path).read_text(encoding="utf-8"))
    drafts = payload.get("drafts", [])
    reviewer_list = [r.strip() for r in reviewers.split(",") if r.strip()]
    out = write_blind_review_package(drafts, output_dir, reviewers=reviewer_list)
    click.echo(f"Blind-review package written to {out}/")
    click.echo(f"  Mapping (segregated): {out}/_mapping.json")


@cli.command()
@click.argument("results_path", type=click.Path(exists=True, dir_okay=False))
def score(results_path: str) -> None:  # pragma: no cover — Phase 2
    """Run Layer 2/4/5 LLM-judge passes on a results JSON. (Phase 2)"""
    click.echo("`draftbench score` lands with Layer 2/4/5 LLM-judge harness — Phase 2.")
    click.echo(f"(Layer 1 metrics for {results_path} are already in the saved JSON.)")


@cli.command()
@click.argument("results_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--format", "fmt", type=click.Choice(["html", "md"]), default="html", show_default=True)
def report(results_path: str, fmt: str) -> None:  # pragma: no cover — Phase 2
    """Generate a shareable scorecard from a results JSON. (Phase 2)"""
    click.echo(f"`draftbench report --format {fmt}` lands with composite scorer — Phase 2.")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()

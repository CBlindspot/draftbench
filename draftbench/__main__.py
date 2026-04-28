"""DraftBench CLI entry point — `draftbench {run,score,export-blind,report}`."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from draftbench import __version__
from draftbench.blind_review import write_blind_review_package
from draftbench.config import BenchmarkConfig
from draftbench.data_loader import DataLoader
from draftbench.harness import BenchmarkRunner
from draftbench.layers.hallucination import HallucinationTaxonomyJudge
from draftbench.layers.jurisdictional import JurisdictionalJudge
from draftbench.layers.section_112_us import Section112USJudge
from draftbench.layers.therasense import TheresenseChecker
from draftbench.scoring.composite import (
    CompositeScore,
    CompositeScorer,
    DimensionScore,
)
from draftbench.scoring.report import HTMLReportGenerator

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
@click.option("--output", type=click.Path(), required=True,
              help="Output scored JSON path.")
@click.option("--judge-model", default="claude-opus-4.7", show_default=True,
              help="Judge model ID (see `draftbench list-models`).")
@click.option("--cross-judge-model", default=None,
              help="Optional cross-family judge model ID (METHODOLOGY.md §10).")
@click.option("--skip-uspto", is_flag=True,
              help="Skip Layer 5A USPTO patent verification (offline mode).")
@click.option("--skip-jurisdictional", is_flag=True,
              help="Skip Layer 4 EP/CN/JP judge.")
@click.option("--skip-taxonomy", is_flag=True,
              help="Skip Layer 5B Class B-E judge.")
@click.option("--limit", type=int, default=None,
              help="Score only the first N succeeded drafts (for testing).")
def score(  # pragma: no cover — orchestration glue, exercised end-to-end
    results_path: str,
    output: str,
    judge_model: str,
    cross_judge_model: str | None,
    skip_uspto: bool,
    skip_jurisdictional: bool,
    skip_taxonomy: bool,
    limit: int | None,
) -> None:
    """Run Layer 2/4/5 LLM-judge passes on a results JSON and write composite scores."""
    payload = json.loads(Path(results_path).read_text(encoding="utf-8"))
    drafts = [d for d in payload.get("drafts", []) if d.get("succeeded")]
    if limit:
        drafts = drafts[:limit]
    if not drafts:
        click.echo("No succeeded drafts to score in input JSON.", err=True)
        sys.exit(1)

    primary_judge = _build_judge(judge_model)
    cross_judge = _build_judge(cross_judge_model) if cross_judge_model else None

    layer2 = Section112USJudge(judge=primary_judge)
    layer4 = JurisdictionalJudge(judge=primary_judge) if not skip_jurisdictional else None
    layer5b = HallucinationTaxonomyJudge(judge=primary_judge) if not skip_taxonomy else None
    therasense = TheresenseChecker() if not skip_uspto else None
    scorer = CompositeScorer()

    composite_scores: list[CompositeScore] = []
    skipped: list[tuple[str, str, str]] = []  # (model, invention, error)
    for d in drafts:
        # Per-draft exception isolation — one bad draft must not abort the whole
        # batch. Layer-internal errors are already tagged via JudgeResult.error;
        # this guard catches unexpected exceptions (rubric-file missing, KeyError
        # on malformed input draft, etc).
        try:
            click.echo(
                f"Scoring [{d['model_name']}] {d['invention_id']} repeat {d.get('repeat', 1)}…"
            )
            draft_text = d.get("output_text") or ""
            l2 = layer2.evaluate(draft_text, cross_judge=cross_judge)
            l4 = layer4.evaluate(draft_text) if layer4 else None
            l5a = therasense.check(draft_text) if therasense else None
            l5b = layer5b.evaluate(draft_text) if layer5b else None
            cs = scorer.score(
                invention_id=d["invention_id"],
                model_name=d["model_name"],
                layer1_metrics=d.get("auto_metrics") or {},
                section_112_us=l2,
                jurisdictional=l4,
                therasense=l5a,
                hallucination_taxonomy=l5b,
            )
            composite_scores.append(cs)
        except Exception as exc:  # noqa: BLE001 — log + continue, don't kill batch
            err = f"{type(exc).__name__}: {exc}"
            click.echo(
                f"  WARN: skipping draft [{d.get('model_name', '?')}] "
                f"{d.get('invention_id', '?')} — {err}",
                err=True,
            )
            skipped.append((d.get("model_name", "?"), d.get("invention_id", "?"), err))

    out_payload = {
        "run_id": payload.get("run_id", "unknown"),
        "started_at": payload.get("started_at"),
        "finished_at": payload.get("finished_at"),
        "judge_model": judge_model,
        "cross_judge_model": cross_judge_model,
        "scores": [_score_to_dict(cs) for cs in composite_scores],
        "drafts": payload.get("drafts", []),  # preserve so report can use cost data
    }
    Path(output).write_text(json.dumps(out_payload, indent=2, ensure_ascii=False))

    if not composite_scores:
        click.echo("\nNo drafts scored successfully — check warnings above.", err=True)
        sys.exit(1)

    avg = sum(c.composite for c in composite_scores) / len(composite_scores)
    kills = sum(1 for c in composite_scores if c.kill_switch_active)
    click.echo(
        f"\nScored {len(composite_scores)} drafts → {output}"
        f"\n  Average composite: {avg:.3f}"
        f"\n  Kill-switches: {kills}"
        + (f"\n  Skipped (errors): {len(skipped)}" if skipped else "")
    )


@cli.command()
@click.argument("scored_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--output", type=click.Path(), required=True, help="Output HTML path.")
@click.option("--format", "fmt", type=click.Choice(["html"]), default="html", show_default=True)
def report(scored_path: str, output: str, fmt: str) -> None:  # pragma: no cover
    """Generate a shareable scorecard (HTML) from a scored results JSON."""
    payload = json.loads(Path(scored_path).read_text(encoding="utf-8"))
    composite_scores = [_dict_to_score(s) for s in payload.get("scores", [])]
    drafts = payload.get("drafts", [])
    metadata = {
        "run_id": payload.get("run_id"),
        "started_at": payload.get("started_at"),
    }
    rendered = HTMLReportGenerator().render(
        composite_scores, run_metadata=metadata, drafts=drafts
    )
    Path(output).write_text(rendered, encoding="utf-8")
    click.echo(f"Report ({fmt}) → {output}")


# ---------------------------------------------------------------------- helpers


def _build_judge(model_id: str):
    """Construct an OpenRouterJudge from the registry. Imported lazily so unit
    tests that don't touch the CLI never need the openai SDK at import time."""
    from draftbench.judges.openrouter_judge import OpenRouterJudge

    if model_id not in MODEL_REGISTRY:
        raise click.UsageError(
            f"Unknown judge model: {model_id}. Run `draftbench list-models`."
        )
    cfg = MODEL_REGISTRY[model_id]
    return OpenRouterJudge(
        model=cfg["openrouter_id"],
        pricing_in=cfg["in"],
        pricing_out=cfg["out"],
        display_name=model_id,
    )


def _score_to_dict(cs: CompositeScore) -> dict:
    return asdict(cs)


def _dict_to_score(data: dict) -> CompositeScore:
    """Reconstruct a CompositeScore from its serialized dict form."""
    dim_scores = {
        int(k): DimensionScore(
            dimension=int(v["dimension"]),
            weight=float(v["weight"]),
            score=v["score"],
            sources=list(v.get("sources", [])),
            note=str(v.get("note", "")),
        )
        for k, v in data.get("dimension_scores", {}).items()
    }
    return CompositeScore(
        invention_id=str(data["invention_id"]),
        model_name=str(data["model_name"]),
        composite=float(data["composite"]),
        coverage=float(data["coverage"]),
        extrapolated_composite=float(data["extrapolated_composite"]),
        dimension_scores=dim_scores,
        kill_switch_active=bool(data.get("kill_switch_active", False)),
        kill_switch_reasons=list(data.get("kill_switch_reasons", [])),
        notes=list(data.get("notes", [])),
    )


def main() -> None:
    cli()


if __name__ == "__main__":
    main()

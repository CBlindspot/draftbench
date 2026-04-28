"""Fetch live OpenRouter pricing for the watched-model list.

Usage:
    python -m scripts.refresh_pricing

Outputs a snapshot to `docs/pricing_snapshot_{date}.json` and prints the
per-model price-and-context table. The hardcoded values in
`draftbench/__main__.py:MODEL_REGISTRY` stay stable for reproducibility — use
this script to detect drift.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import requests

WATCHED = [
    "anthropic/claude-opus-4.7",
    "anthropic/claude-opus-4.6",
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-haiku-4.5",
    "openai/gpt-5.4",
    "openai/gpt-5.4-pro",
    "meta-llama/llama-4-maverick",
    "meta-llama/llama-3.3-70b-instruct",
    "nousresearch/hermes-3-llama-3.1-405b",
    "deepseek/deepseek-r1-0528",
    "deepseek/deepseek-v3.2",
    "qwen/qwen3-max-thinking",
    "qwen/qwen3.6-plus",
]


def main() -> int:
    resp = requests.get("https://openrouter.ai/api/v1/models", timeout=20)
    resp.raise_for_status()
    models = {m["id"]: m for m in resp.json().get("data", [])}

    snapshot: dict = {"fetched_at": date.today().isoformat(), "models": []}

    print(f"{'Model':55s}  {'ctx':>8s}  {'$/1M in':>10s}  {'$/1M out':>10s}")
    for mid in WATCHED:
        m = models.get(mid)
        if not m:
            print(f"{mid:55s}  MISSING")
            continue
        p = m.get("pricing", {})
        ctx = m.get("context_length", 0)
        in_per_1m = float(p.get("prompt", 0)) * 1_000_000
        out_per_1m = float(p.get("completion", 0)) * 1_000_000
        print(f"{mid:55s}  {ctx:>8d}  {in_per_1m:>10.3f}  {out_per_1m:>10.3f}")
        snapshot["models"].append(
            {
                "id": mid,
                "context_length": ctx,
                "pricing_per_1m_in_usd": round(in_per_1m, 4),
                "pricing_per_1m_out_usd": round(out_per_1m, 4),
            }
        )

    out_path = Path(f"docs/pricing_snapshot_{snapshot['fetched_at']}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2))
    print(f"\nSnapshot written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

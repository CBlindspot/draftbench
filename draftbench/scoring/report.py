"""HTML report generator — METHODOLOGY.md §12.

Renders a self-contained HTML scorecard from a list of `CompositeScore` results
plus optional run metadata. Inline CSS, Chart.js loaded via CDN for the cost ×
quality Pareto plot. No template-engine dependency — pure string composition.
"""

from __future__ import annotations

import html
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from draftbench.scoring.composite import CompositeScore


@dataclass
class ModelAggregate:
    """Aggregated stats for one model across its repeats / inventions."""

    model_name: str
    composite_avg: float
    composite_min: float
    composite_max: float
    coverage_avg: float
    extrapolated_avg: float
    kill_switch_count: int
    cost_total_usd: float
    drafts_count: int
    dimension_avgs: dict[int, float | None] = field(default_factory=dict)


class HTMLReportGenerator:
    """Builds a single self-contained HTML report from CompositeScores + run metadata."""

    METHODOLOGY_VERSION = "v1.0-draft"

    def render(
        self,
        composite_scores: list[CompositeScore],
        run_metadata: dict | None = None,
        drafts: list[dict] | None = None,
    ) -> str:
        run_metadata = run_metadata or {}
        drafts = drafts or []

        aggregates = self._aggregate_per_model(composite_scores, drafts)
        sorted_aggregates = sorted(
            aggregates.values(), key=lambda a: a.composite_avg, reverse=True
        )

        parts = [
            self._html_head(run_metadata),
            self._header(run_metadata, len(composite_scores), len(aggregates)),
            self._caveat_v10(),
            self._leaderboard(sorted_aggregates),
            self._dimension_breakdown(sorted_aggregates),
            self._findings_section(composite_scores),
            self._pareto_section(sorted_aggregates),
            self._footer(),
            self._html_tail(sorted_aggregates),
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------ aggregation

    def _aggregate_per_model(
        self,
        composite_scores: list[CompositeScore],
        drafts: list[dict],
    ) -> dict[str, ModelAggregate]:
        # Index drafts by (model_name, invention_id) for cost lookup.
        cost_by_pair: dict[tuple[str, str], float] = defaultdict(float)
        for d in drafts:
            key = (d.get("model_name", ""), d.get("invention_id", ""))
            cost_by_pair[key] += float(d.get("cost_usd", 0.0))

        by_model: dict[str, list[CompositeScore]] = defaultdict(list)
        for cs in composite_scores:
            by_model[cs.model_name].append(cs)

        result: dict[str, ModelAggregate] = {}
        for model, scores in by_model.items():
            composites = [s.composite for s in scores]
            coverages = [s.coverage for s in scores]
            extrapolated = [s.extrapolated_composite for s in scores]
            kill_switches = sum(1 for s in scores if s.kill_switch_active)
            cost_total = sum(
                cost_by_pair.get((model, s.invention_id), 0.0) for s in scores
            )

            dim_avgs: dict[int, float | None] = {}
            for dim_id in range(1, 8):
                vals = [
                    s.dimension_scores[dim_id].score
                    for s in scores
                    if dim_id in s.dimension_scores
                    and s.dimension_scores[dim_id].score is not None
                ]
                dim_avgs[dim_id] = sum(vals) / len(vals) if vals else None

            result[model] = ModelAggregate(
                model_name=model,
                composite_avg=sum(composites) / len(composites),
                composite_min=min(composites),
                composite_max=max(composites),
                coverage_avg=sum(coverages) / len(coverages),
                extrapolated_avg=sum(extrapolated) / len(extrapolated),
                kill_switch_count=kill_switches,
                cost_total_usd=cost_total,
                drafts_count=len(scores),
                dimension_avgs=dim_avgs,
            )
        return result

    # ----------------------------------------------------------------- HTML I/O

    def _html_head(self, run_metadata: dict) -> str:
        run_id = html.escape(str(run_metadata.get("run_id", "draftbench")))
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DraftBench Report — {run_id}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  :root {{
    --fg: #1a1a1a; --muted: #666; --bg: #fff; --accent: #1a4cb8;
    --kill: #b00020; --kill-bg: #fde7e9; --warn: #f0d000; --warn-bg: #fffbe6;
    --critical: #b00; --major: #d80; --minor: #888;
    --border: #e2e2e2; --row-alt: #fafafa;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 1100px; margin: 2rem auto; padding: 0 1rem;
    line-height: 1.55; color: var(--fg); background: var(--bg);
  }}
  h1, h2, h3 {{ font-weight: 600; letter-spacing: -0.01em; }}
  h1 {{ font-size: 2rem; margin-bottom: 0.25rem; }}
  h2 {{ font-size: 1.4rem; margin-top: 2.5rem; padding-bottom: 0.4rem; border-bottom: 1px solid var(--border); }}
  h3 {{ font-size: 1.05rem; }}
  .meta {{ font-size: 0.875rem; color: var(--muted); }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.92rem; }}
  th, td {{ text-align: left; padding: 0.55rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: top; }}
  th {{ background: #f5f5f7; font-weight: 600; }}
  tbody tr:nth-child(even) {{ background: var(--row-alt); }}
  .num {{ font-variant-numeric: tabular-nums; text-align: right; }}
  .score-bar-bg {{ display: inline-block; width: 80px; height: 8px; background: #eee; border-radius: 4px; vertical-align: middle; margin-right: 0.5rem; }}
  .score-bar-fg {{ display: inline-block; height: 8px; background: var(--accent); border-radius: 4px; }}
  .kill-cell {{ background: var(--kill-bg); color: var(--kill); font-weight: 600; }}
  .deferred {{ color: var(--muted); font-style: italic; }}
  .caveat {{ background: var(--warn-bg); border-left: 4px solid var(--warn); padding: 1rem 1.25rem; margin: 1.5rem 0; border-radius: 0 4px 4px 0; }}
  .caveat strong {{ color: #6b5300; }}
  .findings-list {{ margin-top: 1rem; }}
  .finding {{ padding: 0.55rem 0.75rem; margin: 0.4rem 0; border-left: 3px solid var(--minor); background: #fafafa; }}
  .finding.kill {{ border-color: var(--kill); background: var(--kill-bg); }}
  .finding.critical {{ border-color: var(--critical); background: #fff5f5; }}
  .finding.major {{ border-color: var(--major); background: #fffaf0; }}
  .finding-meta {{ font-size: 0.8rem; color: var(--muted); }}
  footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); font-size: 0.85rem; color: var(--muted); }}
  canvas {{ max-width: 100%; height: 320px !important; }}
  .pill {{ display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.75rem; background: #eef2f7; color: var(--accent); }}
  .pill-kill {{ background: var(--kill-bg); color: var(--kill); }}
</style>
</head>
<body>"""

    def _header(self, run_metadata: dict, total_drafts: int, total_models: int) -> str:
        run_id = html.escape(str(run_metadata.get("run_id", "—")))
        started = run_metadata.get("started_at", "")
        try:
            when = datetime.fromisoformat(started.replace("Z", "+00:00")) if started else datetime.now(timezone.utc)
        except (ValueError, TypeError):
            when = datetime.now(timezone.utc)
        date_str = when.strftime("%Y-%m-%d %H:%M UTC")
        return f"""
<header>
  <h1>DraftBench Report</h1>
  <p class="meta">
    Run: <code>{run_id}</code> &middot;
    Methodology {self.METHODOLOGY_VERSION} &middot;
    {date_str} &middot;
    {total_drafts} drafts across {total_models} models
  </p>
</header>"""

    def _caveat_v10(self) -> str:
        return """
<div class="caveat">
  <strong>v1.0-draft scope.</strong> Dim 3 (Durability — Track A historical corpus)
  and Dim 4 (Workflow & UX — Track B attorney edit-time) are deferred to v1.1.
  Dim 6 (Confidentiality) and Dim 7 (Integration & TCO) are vendor metadata
  captured at vendor onboarding, not per-draft. The composite below reflects the
  weighted-available subset of dimensions; the extrapolated column projects to
  full coverage assuming missing dimensions would score the same as scored ones.
</div>"""

    def _leaderboard(self, aggregates: list[ModelAggregate]) -> str:
        rows: list[str] = []
        for rank, agg in enumerate(aggregates, 1):
            kill_cell = (
                f'<td class="kill-cell">{agg.kill_switch_count} drafts killed</td>'
                if agg.kill_switch_count > 0
                else '<td class="num">0</td>'
            )
            rows.append(
                f"""<tr>
  <td class="num">{rank}</td>
  <td><strong>{html.escape(agg.model_name)}</strong></td>
  <td class="num">{self._score_bar(agg.composite_avg)} {agg.composite_avg:.3f}</td>
  <td class="num">{agg.extrapolated_avg:.3f}</td>
  <td class="num">{agg.coverage_avg:.0%}</td>
  <td class="num">{agg.drafts_count}</td>
  {kill_cell}
  <td class="num">${agg.cost_total_usd:.4f}</td>
</tr>"""
            )
        return f"""
<section>
  <h2>Leaderboard</h2>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Model</th><th>Composite</th><th>Extrapolated</th>
        <th>Coverage</th><th>Drafts</th><th>Kill-switch</th><th>Cost</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows) if rows else '<tr><td colspan="8">No drafts scored.</td></tr>'}
    </tbody>
  </table>
</section>"""

    def _dimension_breakdown(self, aggregates: list[ModelAggregate]) -> str:
        rows: list[str] = []
        for agg in aggregates:
            cells = []
            for dim_id in range(1, 8):
                val = agg.dimension_avgs.get(dim_id)
                if val is None:
                    cells.append('<td class="deferred num">—</td>')
                else:
                    cells.append(
                        f'<td class="num">{self._score_bar(val, w=50)} {val:.3f}</td>'
                    )
            rows.append(
                f"<tr><td><strong>{html.escape(agg.model_name)}</strong></td>{''.join(cells)}</tr>"
            )
        return f"""
<section>
  <h2>Per-dimension breakdown</h2>
  <p class="meta">
    Dim 1 — Claim Drafting (35%) &middot;
    Dim 2 — Specification (20%) &middot;
    Dim 3 — Durability (15%, Track A) &middot;
    Dim 4 — Workflow (10%, Track B) &middot;
    Dim 5 — Safety (10%) &middot;
    Dim 6 — Confidentiality (5%) &middot;
    Dim 7 — Integration / TCO (5%)
  </p>
  <table>
    <thead>
      <tr>
        <th>Model</th>
        <th>Dim 1</th><th>Dim 2</th><th>Dim 3</th><th>Dim 4</th>
        <th>Dim 5</th><th>Dim 6</th><th>Dim 7</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows) if rows else '<tr><td colspan="8">No data.</td></tr>'}
    </tbody>
  </table>
</section>"""

    def _findings_section(self, scores: list[CompositeScore]) -> str:
        kill_findings: list[str] = []
        for cs in scores:
            if cs.kill_switch_active:
                for reason in cs.kill_switch_reasons:
                    kill_findings.append(
                        f"""<div class="finding kill">
<strong>KILL-SWITCH</strong>
&middot; <code>{html.escape(cs.model_name)}</code> on <code>{html.escape(cs.invention_id)}</code>
<div>{html.escape(reason)}</div>
</div>"""
                    )
        if not kill_findings:
            inner = '<p class="meta">No Therasense kill-switches triggered. No fabricated prior-art citations detected across this run.</p>'
        else:
            inner = '<div class="findings-list">' + "\n".join(kill_findings) + "</div>"
        return f"""
<section>
  <h2>Therasense kill-switch findings</h2>
  {inner}
</section>"""

    def _pareto_section(self, aggregates: list[ModelAggregate]) -> str:
        if not aggregates or all(a.cost_total_usd == 0 for a in aggregates):
            return """
<section>
  <h2>Cost &times; Quality</h2>
  <p class="meta">No cost data recorded for this run; Pareto plot omitted.</p>
</section>"""
        return """
<section>
  <h2>Cost &times; Quality (Pareto)</h2>
  <p class="meta">Total run cost (USD) on the x-axis, average composite score on the y-axis. Closer to top-left is better.</p>
  <canvas id="paretoChart"></canvas>
</section>"""

    def _footer(self) -> str:
        return f"""
<footer>
  Generated by DraftBench &middot;
  Methodology {self.METHODOLOGY_VERSION} &middot;
  <a href="https://github.com/cblindspot/draftbench">github.com/cblindspot/draftbench</a>
</footer>"""

    def _html_tail(self, aggregates: list[ModelAggregate]) -> str:
        # Build pareto data for chart.js. Skip if no costs.
        pareto_data = [
            {"x": a.cost_total_usd, "y": a.composite_avg, "label": a.model_name}
            for a in aggregates
            if a.cost_total_usd > 0
        ]
        if not pareto_data:
            return "</body>\n</html>"
        data_json = json.dumps(pareto_data)
        return (
            '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>\n'
            "<script>\n"
            f"const paretoData = {data_json};\n"
            """
const ctx = document.getElementById("paretoChart");
new Chart(ctx, {
  type: "scatter",
  data: {
    datasets: [{
      label: "Models",
      data: paretoData,
      backgroundColor: "#1a4cb8",
      pointRadius: 6,
      pointHoverRadius: 8,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { title: { display: true, text: "Cost (USD)" }, beginAtZero: true },
      y: { title: { display: true, text: "Composite score" }, min: 0, max: 1 }
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.raw.label}: $${ctx.raw.x.toFixed(4)} → ${ctx.raw.y.toFixed(3)}`
        }
      },
      legend: { display: false }
    }
  }
});
</script>
</body>
</html>"""
        )

    @staticmethod
    def _score_bar(score: float, w: int = 80) -> str:
        pct = max(0.0, min(1.0, score)) * 100
        return (
            f'<span class="score-bar-bg" style="width:{w}px">'
            f'<span class="score-bar-fg" style="width:{pct * w / 100:.1f}px"></span></span>'
        )

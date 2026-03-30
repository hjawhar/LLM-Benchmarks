"""Reporting utilities: Rich CLI tables and static Plotly HTML charts."""

from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go  # type: ignore[import-untyped]
from rich.console import Console
from rich.table import Table

from llm_bench.models import BenchmarkResult

console = Console()


# ---------------------------------------------------------------------------
# CLI reporter
# ---------------------------------------------------------------------------


class CLIReporter:
    """Renders benchmark results as Rich tables in the terminal."""

    @staticmethod
    def print_results(results: list[BenchmarkResult]) -> None:
        """Print a detailed table with one row per result."""
        table = Table(title="Benchmark Results", show_lines=True)
        table.add_column("Backend", style="cyan")
        table.add_column("Model", style="magenta")
        table.add_column("Prompt", style="green", max_width=30)
        table.add_column("Run", justify="right")
        table.add_column("TTFT (ms)", justify="right")
        table.add_column("TPS", justify="right")
        table.add_column("Prompt Eval TPS", justify="right")
        table.add_column("Load (s)", justify="right")
        table.add_column("Memory (MB)", justify="right")
        table.add_column("Total (s)", justify="right")

        for r in results:
            t = r.timing
            table.add_row(
                r.backend_name,
                r.model_id,
                r.prompt_name,
                str(r.run_index + 1),
                f"{t.ttft_ms:.1f}",
                f"{t.tps:.1f}",
                f"{t.prompt_eval_tps:.1f}",
                f"{t.model_load_time_s:.2f}",
                f"{t.peak_memory_mb:.0f}",
                f"{t.total_duration_s:.2f}",
            )
        console.print(table)

    @staticmethod
    def print_summary(results: list[BenchmarkResult]) -> None:
        """Print an aggregated table with mean and stddev per backend+model."""
        # Group by (backend, model).
        groups: dict[tuple[str, str], list[BenchmarkResult]] = defaultdict(list)
        for r in results:
            groups[(r.backend_name, r.model_id)].append(r)

        table = Table(title="Summary (mean ± stddev)", show_lines=True)
        table.add_column("Backend", style="cyan")
        table.add_column("Model", style="magenta")
        table.add_column("Runs", justify="right")
        table.add_column("TTFT (ms)", justify="right")
        table.add_column("TPS", justify="right")
        table.add_column("Load (s)", justify="right")
        table.add_column("Memory (MB)", justify="right")
        table.add_column("Total (s)", justify="right")

        for (backend, model), group in sorted(groups.items()):
            n = len(group)
            ttfts = [r.timing.ttft_ms for r in group]
            tpss = [r.timing.tps for r in group]
            loads = [r.timing.model_load_time_s for r in group]
            mems = [r.timing.peak_memory_mb for r in group]
            totals = [r.timing.total_duration_s for r in group]

            table.add_row(
                backend,
                model,
                str(n),
                _fmt_mean_std(ttfts),
                _fmt_mean_std(tpss),
                _fmt_mean_std(loads),
                _fmt_mean_std(mems),
                _fmt_mean_std(totals),
            )
        console.print(table)


class MarkdownReporter:
    """Generates a GitHub-flavored Markdown results table."""

    @staticmethod
    def generate(results: list[BenchmarkResult], output_path: Path) -> None:
        """Write a Markdown file with summary and per-prompt breakdown tables.

        The output is designed to render correctly on GitHub (README, issues, PRs).
        """
        groups: dict[tuple[str, str], list[BenchmarkResult]] = defaultdict(list)
        for r in results:
            groups[(r.backend_name, r.model_id)].append(r)

        lines: list[str] = []
        lines.append("## Benchmark Results\n")
        lines.append("### Summary\n")
        lines.append(
            "| Backend | Model | Runs | TTFT (ms) | TPS (tok/s) "
            "| Load (s) | Memory (MB) | Total (s) |"
        )
        lines.append(
            "| ------- | ----- | ---: | --------: | ----------: "
            "| -------: | ----------: | --------: |"
        )

        for (backend, model), group in sorted(groups.items()):
            n = len(group)
            ttft = _fmt_mean_std([r.timing.ttft_ms for r in group])
            tps = _fmt_mean_std([r.timing.tps for r in group])
            load = _fmt_mean_std([r.timing.model_load_time_s for r in group])
            mem = _fmt_mean_std([r.timing.peak_memory_mb for r in group])
            total = _fmt_mean_std([r.timing.total_duration_s for r in group])
            lines.append(
                f"| {backend} | {model} | {n} | {ttft} | {tps} "
                f"| {load} | {mem} | {total} |"
            )

        # Per-prompt breakdown
        lines.append("\n### Per-Prompt Breakdown\n")
        lines.append(
            "| Backend | Model | Prompt | Run "
            "| TTFT (ms) | TPS (tok/s) | Total (s) |"
        )
        lines.append(
            "| ------- | ----- | ------ | --: "
            "| --------: | ----------: | --------: |"
        )
        for r in results:
            t = r.timing
            lines.append(
                f"| {r.backend_name} | {r.model_id} | {r.prompt_name} "
                f"| {r.run_index + 1} | {t.ttft_ms:.1f} | {t.tps:.1f} | {t.total_duration_s:.2f} |"
            )

        lines.append("\n---")
        lines.append(
            f"\n*Generated by llm-bench v{_get_version()} "
            f"| {len(results)} runs across {len(groups)} backend/model configs*\n"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")


def _get_version() -> str:
    """Return package version for report footer."""
    try:
        from llm_bench import __version__
        return __version__
    except Exception:
        return "unknown"


def _fmt_mean_std(values: list[float]) -> str:
    """Format a list of values as 'mean ± stddev'."""
    mean = statistics.mean(values)
    if len(values) >= 2:
        std = statistics.stdev(values)
        return f"{mean:.1f} ± {std:.1f}"
    return f"{mean:.1f}"


# ---------------------------------------------------------------------------
# HTML reporter (Plotly)
# ---------------------------------------------------------------------------


class HTMLReporter:
    """Generates a static HTML report with Plotly bar charts."""

    @staticmethod
    def generate(results: list[BenchmarkResult], output_dir: Path) -> None:
        """Write ``index.html`` into *output_dir* with comparison charts.

        Charts produced:
        - Tokens Per Second comparison
        - Time to First Token comparison
        - Peak memory usage comparison
        - Model load time comparison
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Aggregate by (backend, model) – use means.
        groups: dict[tuple[str, str], list[BenchmarkResult]] = defaultdict(list)
        for r in results:
            groups[(r.backend_name, r.model_id)].append(r)

        labels: list[str] = []
        mean_tps: list[float] = []
        mean_ttft: list[float] = []
        mean_mem: list[float] = []
        mean_load: list[float] = []

        for (backend, model), group in sorted(groups.items()):
            labels.append(f"{backend}\n{model}")
            mean_tps.append(statistics.mean(r.timing.tps for r in group))
            mean_ttft.append(statistics.mean(r.timing.ttft_ms for r in group))
            mean_mem.append(statistics.mean(r.timing.peak_memory_mb for r in group))
            mean_load.append(statistics.mean(r.timing.model_load_time_s for r in group))

        figs: list[tuple[str, go.Figure]] = [
            (
                "Tokens Per Second",
                _bar_chart("Tokens Per Second (higher is better)", labels, mean_tps, "tok/s"),
            ),
            (
                "Time to First Token",
                _bar_chart("Time to First Token (lower is better)", labels, mean_ttft, "ms"),
            ),
            (
                "Peak Memory Usage",
                _bar_chart("Peak Memory Usage", labels, mean_mem, "MB"),
            ),
            (
                "Model Load Time",
                _bar_chart("Model Load Time", labels, mean_load, "s"),
            ),
        ]

        # Build a single HTML page with all charts.
        chart_divs = "\n".join(
            f"<h2>{title}</h2>\n{fig.to_html(full_html=False, include_plotlyjs=False)}"
            for title, fig in figs
        )

        html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>LLM Benchmark Report</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 1100px;
           margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ border-bottom: 2px solid #333; padding-bottom: .5rem; }}
  </style>
</head>
<body>
  <h1>LLM Benchmark Report</h1>
  {chart_divs}
</body>
</html>"""

        (output_dir / "index.html").write_text(html, encoding="utf-8")


def _bar_chart(title: str, labels: list[str], values: list[float], unit: str) -> go.Figure:
    """Create a simple Plotly bar chart."""
    fig = go.Figure(
        data=[go.Bar(x=labels, y=values, text=[f"{v:.1f} {unit}" for v in values])],
    )
    fig.update_layout(
        title=title,
        yaxis_title=unit,
        template="plotly_white",
        height=400,
    )
    return fig

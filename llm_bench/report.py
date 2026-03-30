"""Reporting utilities: Rich CLI tables and GitHub-flavored Markdown."""

from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path

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
        groups: dict[tuple[str, str], list[BenchmarkResult]] = defaultdict(list)
        for r in results:
            groups[(r.backend_name, r.model_id)].append(r)

        table = Table(title="Summary (mean +/- stddev)", show_lines=True)
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


# ---------------------------------------------------------------------------
# Markdown reporter
# ---------------------------------------------------------------------------


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
                f"| {r.run_index + 1} "
                f"| {t.ttft_ms:.1f} | {t.tps:.1f} | {t.total_duration_s:.2f} |"
            )

        lines.append("\n---")
        lines.append(
            f"\n*Generated by llm-bench v{_get_version()} "
            f"| {len(results)} runs "
            f"across {len(groups)} backend/model configs*\n"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_version() -> str:
    """Return package version for report footer."""
    try:
        from llm_bench import __version__

        return __version__
    except Exception:
        return "unknown"


def _fmt_mean_std(values: list[float]) -> str:
    """Format a list of values as 'mean +/- stddev'."""
    mean = statistics.mean(values)
    if len(values) >= 2:
        std = statistics.stdev(values)
        return f"{mean:.1f} +/- {std:.1f}"
    return f"{mean:.1f}"

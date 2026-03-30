"""Click CLI entry point for llm-bench.

Commands:
    run       -- Run benchmarks, output RESULTS.md.
    report    -- Regenerate RESULTS.md from existing SQLite data.
    backends  -- List available backends and installation status.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

if TYPE_CHECKING:
    from llm_bench.models import BenchmarkConfig

console = Console()

RESULTS_PATH = Path("RESULTS.md")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_config(path: Path) -> BenchmarkConfig:
    """Load and validate a benchmark configuration file."""
    from llm_bench.config import load_config

    if not path.exists():
        console.print(f"[bold red]Error:[/] Config file not found: {path}")
        raise SystemExit(1)

    return load_config(path)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="llm-bench")
def cli() -> None:
    """Benchmark LLM inference backends on Apple Silicon."""


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False, path_type=Path),
    default=Path("configs/benchmark.yaml"),
    show_default=True,
    help="Path to benchmark configuration file.",
)
@click.option(
    "--quality",
    is_flag=True,
    default=False,
    help="Enable quality evaluation (perplexity, task accuracy).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=RESULTS_PATH,
    show_default=True,
    help="Path for the Markdown results file.",
)
def run(config_path: Path, quality: bool, output_path: Path) -> None:
    """Run benchmarks and write RESULTS.md."""
    from llm_bench.report import CLIReporter, MarkdownReporter, OutputWriter
    from llm_bench.runner import BenchmarkRunner

    config = _load_config(config_path)

    console.print("\n[bold]LLM Benchmark Runner[/]")
    console.print(f"  Config : {config_path}")
    console.print(f"  Quality: {'enabled' if quality else 'disabled'}")
    console.print(f"  Output : {output_path}\n")

    runner = BenchmarkRunner(config)

    try:
        results = runner.run(quality=quality)
    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrupted by user.[/]")
        raise SystemExit(130) from None

    if not results:
        console.print("[yellow]No results collected.[/]")
        return

    CLIReporter.print_summary(results)
    MarkdownReporter.generate(results, output_path)
    OutputWriter.write(results, Path("benchmarks"))
    console.print(f"\n[green]Results written to {output_path}[/]")
    console.print("[green]Outputs saved to benchmarks/[/]")


# ---------------------------------------------------------------------------
# backends
# ---------------------------------------------------------------------------


@cli.command()
def backends() -> None:
    """List available backends and their installation status."""
    from rich.table import Table

    from llm_bench.backends import get_backend, list_backends

    table = Table(title="LLM Inference Backends")
    table.add_column("Backend", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")

    for name in list_backends():
        backend = get_backend(name)
        available = backend.is_available()
        status = "[green]installed[/]" if available else "[red]not installed[/]"
        table.add_row(name, status)

    console.print(table)

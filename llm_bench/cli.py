"""Click CLI entry point for llm-bench.

Commands:
    run       -- Run benchmarks from a config file.
    report    -- Generate reports from stored results.
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
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("benchmarks/reports"),
    show_default=True,
    help="Directory for HTML report output.",
)
def run(config_path: Path, quality: bool, output_dir: Path) -> None:
    """Run benchmarks from a configuration file."""
    from llm_bench.report import CLIReporter, HTMLReporter, MarkdownReporter
    from llm_bench.runner import BenchmarkRunner
    from llm_bench.storage import ResultsDB

    config = _load_config(config_path)

    console.print("\n[bold]LLM Benchmark Runner[/]")
    console.print(f"  Config : {config_path}")
    console.print(f"  Quality: {'enabled' if quality else 'disabled'}")
    console.print(f"  Output : {output_dir}\n")

    db_path = output_dir / "results.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with ResultsDB(db_path) as db:
        runner = BenchmarkRunner(config, db)

        try:
            results = runner.run(quality=quality)
        except KeyboardInterrupt:
            console.print("\n[yellow]Benchmark interrupted by user.[/]")
            raise SystemExit(130) from None

    if not results:
        console.print("[yellow]No results collected.[/]")
        return

    CLIReporter.print_summary(results)

    output_dir.mkdir(parents=True, exist_ok=True)
    HTMLReporter.generate(results, output_dir)
    md_path = output_dir / "RESULTS.md"
    MarkdownReporter.generate(results, md_path)
    console.print(f"\n[dim]HTML report: {output_dir}/index.html[/]")
    console.print(f"[dim]Markdown report: {md_path}[/]")


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=False, path_type=Path),
    default=Path("benchmarks/reports/results.db"),
    show_default=True,
    help="Path to the SQLite results database.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("benchmarks/reports"),
    show_default=True,
    help="Directory for report output.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["cli", "html", "both"], case_sensitive=False),
    default="both",
    show_default=True,
    help="Report output format.",
)
def report(db_path: Path, output_dir: Path, fmt: str) -> None:
    """Generate reports from existing benchmark results."""
    from llm_bench.report import CLIReporter, HTMLReporter, MarkdownReporter
    from llm_bench.storage import ResultsDB

    if not db_path.exists():
        console.print(f"[bold red]Error:[/] Database not found: {db_path}")
        console.print("[dim]Run benchmarks first with: llm-bench run[/]")
        raise SystemExit(1)

    with ResultsDB(db_path) as db:
        results = db.get_results()

    if not results:
        console.print("[yellow]No results found in database.[/]")
        return

    console.print(
        f"[bold]Generating report[/] ({fmt}) from {len(results)} results..."
    )

    if fmt in ("cli", "both"):
        CLIReporter.print_summary(results)

    if fmt in ("html", "both"):
        output_dir.mkdir(parents=True, exist_ok=True)
        HTMLReporter.generate(results, output_dir)
        md_path = output_dir / "RESULTS.md"
        MarkdownReporter.generate(results, md_path)
        console.print(f"[green]HTML report:[/] {output_dir}/index.html")
        console.print(f"[green]Markdown report:[/] {md_path}")


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

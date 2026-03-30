"""Click CLI entry point for llm-bench.

Commands:
    run       — Run benchmarks from a config file.
    report    — Generate reports from stored results.
    backends  — List available backends and installation status.
    models    — List available models for a backend.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_config(path: Path) -> "BenchmarkConfig":
    """Load and validate a benchmark configuration file."""
    from llm_bench.config import load_config

    if not path.exists():
        console.print(f"[bold red]Error:[/] Config file not found: {path}")
        raise SystemExit(1)

    return load_config(path)


def _get_registry() -> "BackendRegistry":
    """Return the global backend registry."""
    from llm_bench.backends import get_registry

    return get_registry()


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
    from llm_bench.runner import BenchmarkRunner

    config = _load_config(config_path)

    console.print(f"\n[bold]LLM Benchmark Runner[/]")
    console.print(f"  Config : {config_path}")
    console.print(f"  Quality: {'enabled' if quality else 'disabled'}")
    console.print(f"  Output : {output_dir}\n")

    runner = BenchmarkRunner(config=config, quality=quality, output_dir=output_dir)

    try:
        results = runner.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrupted by user.[/]")
        raise SystemExit(130)

    # Summary table
    if not results:
        console.print("[yellow]No results collected.[/]")
        return

    table = Table(title="Benchmark Results Summary", show_lines=True)
    table.add_column("Backend", style="cyan", no_wrap=True)
    table.add_column("Model", style="green")
    table.add_column("Prompt", style="magenta")
    table.add_column("TTFT (ms)", justify="right")
    table.add_column("TPS (tok/s)", justify="right")
    table.add_column("Memory (MB)", justify="right")
    table.add_column("Duration (s)", justify="right")
    if quality:
        table.add_column("Quality", justify="right")

    for r in results:
        row: list[str] = [
            r.backend,
            r.model,
            r.prompt_name,
            f"{r.metrics.ttft_ms:.1f}",
            f"{r.metrics.tokens_per_second:.1f}",
            f"{r.metrics.peak_memory_mb:.0f}",
            f"{r.metrics.total_duration_s:.2f}",
        ]
        if quality:
            score = r.quality_score if r.quality_score is not None else float("nan")
            row.append(f"{score:.2f}")
        table.add_row(*row)

    console.print()
    console.print(table)
    console.print(f"\n[dim]Results stored. Reports in {output_dir}/[/]")


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=False, path_type=Path),
    default=Path("benchmarks/results.db"),
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
    from llm_bench.report import generate_report
    from llm_bench.storage import ResultStore

    if not db_path.exists():
        console.print(f"[bold red]Error:[/] Database not found: {db_path}")
        console.print("[dim]Run benchmarks first with: llm-bench run[/]")
        raise SystemExit(1)

    store = ResultStore(db_path)
    results = store.load_all()

    if not results:
        console.print("[yellow]No results found in database.[/]")
        return

    console.print(f"[bold]Generating report[/] ({fmt}) from {len(results)} results...")

    if fmt in ("cli", "both"):
        # Print a summary table to the console.
        table = Table(title="Benchmark Results", show_lines=True)
        table.add_column("Backend", style="cyan", no_wrap=True)
        table.add_column("Model", style="green")
        table.add_column("TTFT (ms)", justify="right")
        table.add_column("TPS (tok/s)", justify="right")
        table.add_column("Memory (MB)", justify="right")
        table.add_column("Duration (s)", justify="right")

        for r in results:
            table.add_row(
                r.backend,
                r.model,
                f"{r.metrics.ttft_ms:.1f}",
                f"{r.metrics.tokens_per_second:.1f}",
                f"{r.metrics.peak_memory_mb:.0f}",
                f"{r.metrics.total_duration_s:.2f}",
            )
        console.print(table)

    if fmt in ("html", "both"):
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = generate_report(results, output_dir)
        console.print(f"[green]HTML report written to:[/] {html_path}")


# ---------------------------------------------------------------------------
# backends
# ---------------------------------------------------------------------------


@cli.command()
def backends() -> None:
    """List available backends and their installation status."""
    registry = _get_registry()

    table = Table(title="LLM Inference Backends")
    table.add_column("Backend", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Package", style="dim")

    for backend in registry.list_backends():
        available = backend.is_available()
        status = "[green]installed[/]" if available else "[red]not installed[/]"
        # Each backend exposes its pip-installable package name.
        package = getattr(backend, "package_name", "—")
        table.add_row(backend.name, status, package)

    console.print(table)


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--backend",
    "backend_name",
    type=str,
    default=None,
    help="Filter models by backend name.",
)
def models(backend_name: str | None) -> None:
    """List available models for a backend."""
    registry = _get_registry()

    target_backends = (
        [registry.get(backend_name)] if backend_name else registry.list_backends()
    )

    for backend in target_backends:
        if not backend.is_available():
            console.print(
                f"[yellow]{backend.name}:[/] not installed — cannot list models."
            )
            continue

        console.print(f"\n[bold cyan]{backend.name}[/]")
        try:
            model_list = backend.list_models()
        except NotImplementedError:
            console.print("  [dim]Model listing not supported by this backend.[/]")
            continue

        if not model_list:
            console.print("  [dim]No models found.[/]")
            continue

        for m in model_list:
            console.print(f"  • {m}")

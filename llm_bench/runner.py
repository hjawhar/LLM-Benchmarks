"""Benchmark orchestration: drives backends, collects metrics, stores results."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from rich.console import Console

from llm_bench.backends import get_backend
from llm_bench.backends.base import Backend
from llm_bench.metrics import MetricsCollector
from llm_bench.models import (
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkSettings,
    TimingMetrics,
)
from llm_bench.prompts import resolve_prompts
from llm_bench.storage import ResultsDB

logger = logging.getLogger(__name__)
console = Console()


class BenchmarkRunner:
    """Orchestrates benchmark runs across backends, models, and prompts.

    Coordinates warmup, timed generation, optional quality evaluation,
    cool-down pauses, and persistence to the results database.
    """

    def __init__(self, config: BenchmarkConfig, db: ResultsDB) -> None:
        self._config = config
        self._db = db

    # -- backend resolution --------------------------------------------------

    def _resolve_backends(self) -> list[Backend]:
        """Instantiate available backends declared in config.

        Backends whose ``is_available()`` returns False are logged and skipped.
        """
        backends: list[Backend] = []
        for bc in self._config.backends:
            try:
                instance = get_backend(bc.name)
            except KeyError:
                logger.warning("Unknown backend '%s' -- skipping", bc.name)
                continue
            except Exception:
                logger.warning(
                    "Failed to instantiate backend '%s' -- skipping",
                    bc.name,
                    exc_info=True,
                )
                continue
            if not instance.is_available():
                logger.warning(
                    "Backend '%s' is not available -- skipping", bc.name
                )
                continue
            backends.append(instance)
        return backends

    # -- prompt resolution ---------------------------------------------------

    def _load_prompts(self) -> list[tuple[str, str]]:
        """Return a list of ``(name, text)`` pairs from config prompt entries."""
        return resolve_prompts(self._config.prompts)

    # -- single run ----------------------------------------------------------

    def run_single(
        self,
        backend: Backend,
        model_id: str,
        prompt: str,
        max_tokens: int,
    ) -> tuple[str, TimingMetrics]:
        """Execute a single generation and return ``(output_text, timing)``.

        The backend must already have the model loaded.
        """
        collector = MetricsCollector()

        collector.start_generation()
        result = backend.generate(prompt, max_tokens)

        # generate() returns tuple[str, TimingMetrics | None] per protocol.
        # Unpack: if backend provides its own timing, prefer it.
        if isinstance(result, tuple):
            output, backend_timing = result
        else:
            output = result
            backend_timing = None

        collector.record_first_token()
        # Count output tokens (approximate: split on whitespace).
        # A proper implementation would use the backend's tokenizer.
        token_count = len(output.split()) if output else 0
        for _ in range(token_count):
            collector.record_token()
        collector.end_generation()

        timing = backend_timing if backend_timing is not None else collector.collect()
        return output, timing

    # -- main loop -----------------------------------------------------------

    def run(self, quality: bool = False) -> list[BenchmarkResult]:
        """Execute the full benchmark matrix and return all results.

        Parameters
        ----------
        quality:
            If True, run optional quality evaluation (perplexity, task accuracy).
            Currently a placeholder.
        """
        settings: BenchmarkSettings = self._config.settings
        backends = self._resolve_backends()
        prompts = self._load_prompts()
        results: list[BenchmarkResult] = []

        if not backends:
            console.print(
                "[bold red]No available backends -- nothing to run.[/bold red]"
            )
            return results

        if not prompts:
            console.print(
                "[bold red]No valid prompts -- nothing to run.[/bold red]"
            )
            return results

        backend_options: dict[str, dict[str, object]] = {
            bc.name: dict(bc.options) for bc in self._config.backends
        }
        backend_models: dict[str, list[str]] = {
            bc.name: list(bc.models) for bc in self._config.backends
        }

        for backend in backends:
            models = backend_models.get(backend.name, [])
            opts = backend_options.get(backend.name, {})

            for model_id in models:
                # Load model (timed)
                collector = MetricsCollector()
                collector.start_model_load()
                try:
                    backend.load_model(model_id, **opts)
                except Exception:
                    logger.error(
                        "Failed to load model '%s' on backend '%s' -- skipping",
                        model_id,
                        backend.name,
                        exc_info=True,
                    )
                    continue
                collector.end_model_load()
                model_load_timing = collector.collect()

                for prompt_name, prompt_text in prompts:
                    # Warmup runs (discarded)
                    for _ in range(settings.warmup_runs):
                        try:
                            self.run_single(
                                backend, model_id, prompt_text, settings.max_tokens
                            )
                        except Exception:
                            logger.debug("Warmup run failed", exc_info=True)

                    # Timed runs
                    for run_idx in range(settings.runs_per_config):
                        console.print(
                            f"  [cyan]{backend.name}[/cyan] | {model_id} | "
                            f"{prompt_name} | run {run_idx + 1}/{settings.runs_per_config}"
                        )
                        try:
                            output_text, timing = self.run_single(
                                backend, model_id, prompt_text, settings.max_tokens
                            )
                        except Exception:
                            logger.error(
                                "Generation failed: %s / %s / %s run %d",
                                backend.name,
                                model_id,
                                prompt_name,
                                run_idx,
                                exc_info=True,
                            )
                            continue

                        # Override model_load_time from the pre-measured load.
                        timing = timing.model_copy(
                            update={
                                "model_load_time_s": model_load_timing.model_load_time_s
                            }
                        )

                        result = BenchmarkResult(
                            backend_name=backend.name,
                            model_id=model_id,
                            prompt_name=prompt_name,
                            prompt_text=prompt_text,
                            output_text=output_text,
                            timing=timing,
                            quality=None,  # placeholder for quality evaluation
                            run_index=run_idx,
                            timestamp=datetime.now(UTC),
                            settings=settings,
                        )
                        results.append(result)
                        self._db.save_result(result)

                        # Cool-down between runs.
                        if settings.cool_down_seconds > 0:
                            time.sleep(settings.cool_down_seconds)

        console.print(
            f"\n[bold green]Completed {len(results)} benchmark run(s).[/bold green]"
        )
        return results

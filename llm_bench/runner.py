"""Benchmark orchestration: drives backends, collects metrics, stores results."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from rich.console import Console

from llm_bench.metrics import MetricsCollector
from llm_bench.models import (
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkSettings,
    TimingMetrics,
)
from llm_bench.storage import ResultsDB

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# Backend protocol – every inference backend must satisfy this contract
# ---------------------------------------------------------------------------


@runtime_checkable
class Backend(Protocol):
    """Public contract that every inference backend must implement."""

    @property
    def name(self) -> str:
        """Unique backend identifier (e.g. ``'mlx-lm'``)."""
        ...

    def is_available(self) -> bool:
        """Return True if the backend's runtime dependencies are importable."""
        ...

    def load_model(self, model_id: str, **options: object) -> None:
        """Load *model_id* into memory."""
        ...

    def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate up to *max_tokens* tokens and return the output text."""
        ...


# ---------------------------------------------------------------------------
# Built-in prompt catalogue
# ---------------------------------------------------------------------------

_BUILTIN_PROMPTS: dict[str, str] = {
    "short_qa": "What is the capital of France?",
    "summarization": (
        "Summarize the following paragraph in one sentence:\n\n"
        "The Industrial Revolution, which took place from the 18th to 19th centuries, "
        "was a period during which predominantly agrarian, rural societies in Europe "
        "and America became industrial and urban."
    ),
    "code_generation": "Write a Python function that computes the Fibonacci sequence up to n terms.",
    "creative_writing": (
        "Write a short story (about 200 words) about a robot discovering emotions for the first time."
    ),
    "reasoning": (
        "If all roses are flowers and some flowers fade quickly, "
        "can we conclude that some roses fade quickly? Explain your reasoning step by step."
    ),
}


# ---------------------------------------------------------------------------
# Registry – maps backend config names to concrete classes
# ---------------------------------------------------------------------------

# Lazy import map so we don't pull in heavy dependencies at module level.
_BACKEND_REGISTRY: dict[str, str] = {
    "mlx-lm": "llm_bench.backends.mlx_backend.MlxBackend",
    "ollama": "llm_bench.backends.ollama_backend.OllamaBackend",
    "llama.cpp": "llm_bench.backends.llamacpp_backend.LlamaCppBackend",
    "vllm": "llm_bench.backends.vllm_backend.VllmBackend",
}


def _import_backend(dotted_path: str) -> type[Backend]:
    """Import a backend class from its fully-qualified dotted path."""
    module_path, _, class_name = dotted_path.rpartition(".")
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# BenchmarkRunner
# ---------------------------------------------------------------------------


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
            dotted = _BACKEND_REGISTRY.get(bc.name)
            if dotted is None:
                logger.warning("Unknown backend '%s' – skipping", bc.name)
                continue
            try:
                cls = _import_backend(dotted)
                instance = cls()  # type: ignore[call-arg]
            except Exception:
                logger.warning("Failed to import backend '%s' – skipping", bc.name, exc_info=True)
                continue
            if not instance.is_available():
                logger.warning("Backend '%s' is not available – skipping", bc.name)
                continue
            backends.append(instance)
        return backends

    # -- prompt resolution ---------------------------------------------------

    def _load_prompts(self) -> list[tuple[str, str]]:
        """Return a list of ``(name, text)`` pairs from config prompt entries."""
        prompts: list[tuple[str, str]] = []
        for pc in self._config.prompts:
            if pc.builtin is not None:
                text = _BUILTIN_PROMPTS.get(pc.builtin)
                if text is None:
                    logger.warning(
                        "Unknown built-in prompt '%s' – skipping. "
                        "Available: %s",
                        pc.builtin,
                        ", ".join(sorted(_BUILTIN_PROMPTS)),
                    )
                    continue
                prompts.append((pc.builtin, text))
            elif pc.custom is not None:
                # Use first 40 chars as the prompt name for display.
                name = pc.custom[:40].replace("\n", " ")
                prompts.append((name, pc.custom))
        return prompts

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
        output = backend.generate(prompt, max_tokens)
        # For streaming backends the collector hooks would be called inside
        # generate(); for non-streaming we mark first-token here as an
        # approximation.
        collector.record_first_token()
        for _ in output:
            collector.record_token()
        collector.end_generation()

        return output, collector.collect()

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
            console.print("[bold red]No available backends – nothing to run.[/bold red]")
            return results

        if not prompts:
            console.print("[bold red]No valid prompts – nothing to run.[/bold red]")
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
                        "Failed to load model '%s' on backend '%s' – skipping",
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
                            self.run_single(backend, model_id, prompt_text, settings.max_tokens)
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
                            update={"model_load_time_s": model_load_timing.model_load_time_s}
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
                            timestamp=datetime.now(timezone.utc),
                            settings=settings,
                        )
                        results.append(result)
                        self._db.save_result(result)

                        # Cool-down between runs.
                        if settings.cool_down_seconds > 0:
                            time.sleep(settings.cool_down_seconds)

        console.print(f"\n[bold green]Completed {len(results)} benchmark run(s).[/bold green]")
        return results

"""Ollama backend communicating with the Ollama server via its Python client."""

from __future__ import annotations

import time
from collections.abc import Iterator

from llm_bench.backends.base import BackendError
from llm_bench.metrics import measure_memory
from llm_bench.models import TimingMetrics


class OllamaBackend:
    """Backend using the ``ollama`` Python client.

    Requires the Ollama server to be running locally (``ollama serve``).
    Model identifiers are Ollama tags (e.g. ``llama3:8b``).
    """

    name: str = "ollama"

    _DEFAULT_HOST = "http://localhost:11434"

    def __init__(self, host: str | None = None) -> None:
        self._host = host or self._DEFAULT_HOST
        self._model_id: str | None = None

    # ------------------------------------------------------------------
    # Protocol
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check for ``ollama`` library and a reachable server."""
        try:
            import ollama as _  # noqa: F401
        except ImportError:
            return False

        # Probe the server — a connection failure means it's not running.
        try:
            import urllib.request

            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2):
                pass
        except Exception:
            return False
        return True

    def load_model(self, model_id: str, **kwargs: object) -> None:
        """Pull the model if absent, then warm it up with a dummy request.

        Args:
            model_id: Ollama model tag (e.g. ``llama3:8b``).
        """
        try:
            import ollama
        except ImportError as exc:
            raise BackendError(self.name, "ollama is not installed", exc) from exc

        try:
            # Pull if not already present (idempotent).
            ollama.pull(model_id)
        except Exception as exc:
            raise BackendError(self.name, f"failed to pull model '{model_id}'", exc) from exc

        # Warm-up: force model load into GPU memory.
        try:
            start_ns = time.perf_counter_ns()
            ollama.generate(model=model_id, prompt="warmup", options={"num_predict": 1})
            load_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        except Exception as exc:
            raise BackendError(
                self.name, f"warm-up generation failed for '{model_id}'", exc
            ) from exc

        self._model_id = model_id
        self._last_load_ms = load_ms

    def generate(self, prompt: str, max_tokens: int) -> tuple[str, TimingMetrics | None]:
        """Run non-streaming generation and extract Ollama's native timing.

        Ollama returns durations in nanoseconds; we convert to our standard
        units (ms, seconds, tok/s).
        """
        if self._model_id is None:
            raise BackendError(self.name, "no model loaded — call load_model() first")

        try:
            import ollama
        except ImportError as exc:
            raise BackendError(self.name, "ollama is not installed", exc) from exc

        try:
            resp = ollama.generate(
                model=self._model_id,
                prompt=prompt,
                options={"num_predict": max_tokens},
                stream=False,
            )
        except Exception as exc:
            raise BackendError(self.name, "generation failed", exc) from exc

        text: str = resp.get("response", "")

        # Ollama reports durations in nanoseconds.
        eval_count = resp.get("eval_count", 0)
        eval_duration_ns = resp.get("eval_duration", 0)
        prompt_eval_count = resp.get("prompt_eval_count", 0)
        prompt_eval_duration_ns = resp.get("prompt_eval_duration", 0)
        load_duration_ns = resp.get("load_duration", 0)
        total_duration_ns = resp.get("total_duration", 0)

        tps = (
            (eval_count / (eval_duration_ns / 1_000_000_000))
            if eval_duration_ns > 0
            else 0.0
        )
        prompt_eval_tps = (
            (prompt_eval_count / (prompt_eval_duration_ns / 1_000_000_000))
            if prompt_eval_duration_ns > 0
            else 0.0
        )

        # TTFT approximation: prompt eval duration is the closest proxy
        # in non-streaming mode (time before first output token).
        ttft_ms = prompt_eval_duration_ns / 1_000_000 if prompt_eval_duration_ns > 0 else 0.0

        metrics = TimingMetrics(
            ttft_ms=ttft_ms,
            tps=tps,
            prompt_eval_tps=prompt_eval_tps,
            model_load_time_s=load_duration_ns / 1_000_000_000,
            peak_memory_mb=measure_memory(),
            total_duration_s=total_duration_ns / 1_000_000_000,
        )
        return text, metrics

    def stream(self, prompt: str, max_tokens: int) -> Iterator[str]:
        """Stream tokens from Ollama."""
        if self._model_id is None:
            raise BackendError(self.name, "no model loaded — call load_model() first")

        try:
            import ollama
        except ImportError as exc:
            raise BackendError(self.name, "ollama is not installed", exc) from exc

        try:
            for chunk in ollama.generate(
                model=self._model_id,
                prompt=prompt,
                options={"num_predict": max_tokens},
                stream=True,
            ):
                token = chunk.get("response", "")
                if token:
                    yield token
        except Exception as exc:
            raise BackendError(self.name, "streaming failed", exc) from exc

    def unload_model(self) -> None:
        """Unload the model from Ollama server memory."""
        if self._model_id is None:
            return

        try:
            import ollama

            # Setting keep_alive=0 tells the server to unload immediately.
            ollama.generate(
                model=self._model_id,
                prompt="",
                keep_alive=0,
                options={"num_predict": 0},
            )
        except Exception:
            # Best-effort; server may already be down.
            pass
        self._model_id = None

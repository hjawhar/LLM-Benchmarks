"""llama-cpp-python backend for GGUF model inference."""

from __future__ import annotations

import gc
import os
import time
from collections.abc import Iterator

from llm_bench.backends.base import BackendError
from llm_bench.metrics import measure_memory
from llm_bench.models import TimingMetrics


class LlamaCppBackend:
    """Backend using ``llama-cpp-python`` for CPU/Metal GGUF inference.

    Model identifiers are **file paths** to ``.gguf`` files, not HuggingFace
    repo IDs.
    """

    name: str = "llama-cpp"

    def __init__(self, n_ctx: int = 2048) -> None:
        self._n_ctx = n_ctx
        self._model: object | None = None
        self._model_id: str | None = None
        self._last_load_ms: float = 0.0

    # ------------------------------------------------------------------
    # Protocol
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check for ``llama_cpp`` library."""
        try:
            import llama_cpp as _  # noqa: F401
        except ImportError:
            return False
        return True

    def load_model(self, model_id: str, **kwargs: object) -> None:
        """Load a GGUF model from disk.

        Args:
            model_id: Filesystem path to a ``.gguf`` model file.
            **kwargs: Forwarded to ``llama_cpp.Llama()``.
        """
        if not os.path.isfile(model_id):
            raise BackendError(
                self.name, f"model file not found: {model_id!r} — llama.cpp requires a GGUF path"
            )

        try:
            import llama_cpp
        except ImportError as exc:
            raise BackendError(self.name, "llama-cpp-python is not installed", exc) from exc

        try:
            start_ns = time.perf_counter_ns()
            model = llama_cpp.Llama(
                model_path=model_id,
                n_ctx=int(kwargs.get("n_ctx", self._n_ctx)),  # type: ignore[arg-type]
                verbose=False,
            )
            self._last_load_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        except Exception as exc:
            raise BackendError(self.name, f"failed to load model '{model_id}'", exc) from exc

        self._model = model
        self._model_id = model_id

    def generate(self, prompt: str, max_tokens: int) -> tuple[str, TimingMetrics | None]:
        """Run completion and extract timing from llama.cpp usage stats."""
        if self._model is None:
            raise BackendError(self.name, "no model loaded — call load_model() first")

        try:
            start_ns = time.perf_counter_ns()
            resp = self._model.create_completion(  # type: ignore[union-attr]
                prompt,
                max_tokens=max_tokens,
            )
            total_ns = time.perf_counter_ns() - start_ns
        except Exception as exc:
            raise BackendError(self.name, "generation failed", exc) from exc

        total_s = total_ns / 1_000_000_000

        text = resp["choices"][0]["text"] if resp.get("choices") else ""

        # llama-cpp-python exposes usage in the response dict.
        usage = resp.get("usage", {})
        output_tokens = usage.get("completion_tokens", 0)
        prompt_tokens = usage.get("prompt_tokens", 0)

        tps = output_tokens / total_s if total_s > 0 and output_tokens else 0.0

        metrics = TimingMetrics(
            ttft_ms=total_ns / 1_000_000,  # non-streaming: TTFT ~ total time
            tps=tps,
            prompt_eval_tps=prompt_tokens / total_s if total_s > 0 and prompt_tokens else 0.0,
            model_load_time_s=self._last_load_ms / 1000,
            peak_memory_mb=measure_memory(),
            total_duration_s=total_s,
        )
        return text, metrics

    def stream(self, prompt: str, max_tokens: int) -> Iterator[str]:
        """Stream tokens via llama.cpp completion."""
        if self._model is None:
            raise BackendError(self.name, "no model loaded — call load_model() first")

        try:
            for chunk in self._model.create_completion(  # type: ignore[union-attr]
                prompt,
                max_tokens=max_tokens,
                stream=True,
            ):
                choices = chunk.get("choices", [])
                if choices:
                    token = choices[0].get("text", "")
                    if token:
                        yield token
        except Exception as exc:
            raise BackendError(self.name, "streaming failed", exc) from exc

    def unload_model(self) -> None:
        """Release model resources."""
        self._model = None
        self._model_id = None
        gc.collect()

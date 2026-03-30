"""MLX-LM backend for Apple Silicon native inference."""

from __future__ import annotations

import gc
import platform
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING

from llm_bench.backends.base import BackendError
from llm_bench.metrics import measure_memory
from llm_bench.models import TimingMetrics

if TYPE_CHECKING:
    pass  # mlx_lm types not publicly exported


class MLXLMBackend:
    """Backend using the ``mlx-lm`` library for Apple Silicon GPUs.

    Only available on ARM-based macOS (Apple Silicon).  Model identifiers
    are HuggingFace repo IDs (e.g. ``mlx-community/Llama-3-8B-4bit``).
    """

    name: str = "mlx-lm"

    def __init__(self) -> None:
        self._model: object | None = None
        self._tokenizer: object | None = None
        self._model_id: str | None = None

    # ------------------------------------------------------------------
    # Protocol
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check for mlx_lm on Apple Silicon."""
        if platform.machine() not in ("arm64", "aarch64") or platform.system() != "Darwin":
            return False
        try:
            import mlx_lm as _  # noqa: F401
        except ImportError:
            return False
        return True

    def load_model(self, model_id: str, **kwargs: object) -> None:
        """Load a model via ``mlx_lm.load``.

        Args:
            model_id: HuggingFace model ID (e.g. ``mlx-community/Llama-3-8B-4bit``).
            **kwargs: Forwarded to ``mlx_lm.load``.
        """
        try:
            import mlx_lm
        except ImportError as exc:
            raise BackendError(self.name, "mlx_lm is not installed", exc) from exc

        try:
            start_ns = time.perf_counter_ns()
            model, tokenizer = mlx_lm.load(model_id, **kwargs)  # type: ignore[arg-type]
            load_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        except Exception as exc:
            raise BackendError(self.name, f"failed to load model '{model_id}'", exc) from exc

        self._model = model
        self._tokenizer = tokenizer
        self._model_id = model_id
        self._last_load_ms = load_ms

    def generate(self, prompt: str, max_tokens: int) -> tuple[str, TimingMetrics | None]:
        """Generate text using ``mlx_lm.generate``.

        Wraps the call with nanosecond-precision timers for TTFT and total
        duration, and counts output tokens via the tokenizer.
        """
        if self._model is None or self._tokenizer is None:
            raise BackendError(self.name, "no model loaded — call load_model() first")

        try:
            import mlx_lm
        except ImportError as exc:
            raise BackendError(self.name, "mlx_lm is not installed", exc) from exc

        try:
            start_ns = time.perf_counter_ns()
            text: str = mlx_lm.generate(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
            )
            total_ns = time.perf_counter_ns() - start_ns
        except Exception as exc:
            raise BackendError(self.name, "generation failed", exc) from exc

        total_s = total_ns / 1_000_000_000
        # Approximate token count via tokenizer
        try:
            output_tokens = len(self._tokenizer.encode(text))  # type: ignore[union-attr]
            prompt_tokens = len(self._tokenizer.encode(prompt))  # type: ignore[union-attr]
        except Exception:
            output_tokens = 0
            prompt_tokens = 0

        tps = output_tokens / total_s if total_s > 0 and output_tokens else 0.0

        metrics = TimingMetrics(
            ttft_ms=total_ns / 1_000_000,  # non-streaming: TTFT ~ total time
            tps=tps,
            prompt_eval_tps=prompt_tokens / total_s if total_s > 0 and prompt_tokens else 0.0,
            model_load_time_s=getattr(self, "_last_load_ms", 0.0) / 1000,
            peak_memory_mb=measure_memory(),
            total_duration_s=total_s,
        )
        return text, metrics

    def stream(self, prompt: str, max_tokens: int) -> Iterator[str]:
        """Stream tokens via ``mlx_lm.stream_generate``."""
        if self._model is None or self._tokenizer is None:
            raise BackendError(self.name, "no model loaded — call load_model() first")

        try:
            import mlx_lm
        except ImportError as exc:
            raise BackendError(self.name, "mlx_lm is not installed", exc) from exc

        try:
            for chunk in mlx_lm.stream_generate(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
            ):
                # stream_generate yields (text, metadata) tuples or strings
                # depending on version; handle both.
                if isinstance(chunk, tuple):
                    yield chunk[0]
                else:
                    yield str(chunk)
        except Exception as exc:
            raise BackendError(self.name, "streaming failed", exc) from exc

    def unload_model(self) -> None:
        """Release model and tokenizer, reclaim memory."""
        self._model = None
        self._tokenizer = None
        self._model_id = None
        gc.collect()

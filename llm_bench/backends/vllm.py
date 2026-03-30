"""vLLM backend for high-throughput inference (requires vllm-metal on macOS)."""

from __future__ import annotations

import gc
import time
from typing import Iterator

from llm_bench.backends.base import BackendError
from llm_bench.models import TimingMetrics


class VLLMBackend:
    """Backend using vLLM's offline ``LLM`` engine.

    On macOS Apple Silicon, requires the ``vllm-metal`` package rather than
    stock ``vllm``.  Model identifiers are HuggingFace repo IDs.

    Note: vLLM's offline mode does not support true streaming — the
    ``stream()`` method iterates over completed output tokens after
    generation finishes.
    """

    name: str = "vllm"

    def __init__(self) -> None:
        self._engine: object | None = None
        self._model_id: str | None = None
        self._last_load_ms: float = 0.0

    # ------------------------------------------------------------------
    # Protocol
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check for ``vllm`` library (or ``vllm-metal`` on macOS)."""
        try:
            import vllm as _  # noqa: F401
        except ImportError:
            return False
        return True

    def load_model(self, model_id: str, **kwargs: object) -> None:
        """Instantiate the vLLM engine for the given model.

        Args:
            model_id: HuggingFace model ID.
            **kwargs: Forwarded to ``vllm.LLM()``.
        """
        try:
            import vllm
        except ImportError as exc:
            raise BackendError(self.name, "vllm is not installed", exc) from exc

        try:
            start_ns = time.perf_counter_ns()
            engine = vllm.LLM(model=model_id, **kwargs)  # type: ignore[arg-type]
            self._last_load_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        except Exception as exc:
            raise BackendError(self.name, f"failed to load model '{model_id}'", exc) from exc

        self._engine = engine
        self._model_id = model_id

    def generate(self, prompt: str, max_tokens: int) -> tuple[str, TimingMetrics | None]:
        """Generate text via vLLM's offline batch interface."""
        if self._engine is None:
            raise BackendError(self.name, "no model loaded — call load_model() first")

        try:
            from vllm import SamplingParams
        except ImportError as exc:
            raise BackendError(self.name, "vllm is not installed", exc) from exc

        try:
            params = SamplingParams(max_tokens=max_tokens)
            start_ns = time.perf_counter_ns()
            outputs = self._engine.generate([prompt], params)  # type: ignore[union-attr]
            total_ns = time.perf_counter_ns() - start_ns
        except Exception as exc:
            raise BackendError(self.name, "generation failed", exc) from exc

        total_s = total_ns / 1_000_000_000

        # vLLM returns a list of RequestOutput; first element for our single prompt.
        output = outputs[0]
        text = output.outputs[0].text if output.outputs else ""
        output_tokens = len(output.outputs[0].token_ids) if output.outputs else 0
        prompt_tokens = len(output.prompt_token_ids) if hasattr(output, "prompt_token_ids") else 0

        tps = output_tokens / total_s if total_s > 0 and output_tokens else 0.0

        metrics = TimingMetrics(
            ttft_ms=None,
            tps=tps,
            prompt_eval_tps=None,
            model_load_time_s=self._last_load_ms / 1000,
            peak_memory_mb=None,
            total_duration_s=total_s,
            output_tokens=output_tokens,
            prompt_tokens=prompt_tokens,
        )
        return text, metrics

    def stream(self, prompt: str, max_tokens: int) -> Iterator[str]:
        """Simulate streaming by iterating over output tokens post-generation.

        vLLM's offline ``LLM`` engine does not support incremental delivery;
        this method generates the full response then yields each token string
        sequentially, which is useful for API-compatible wrappers but does
        not represent true streaming latency.
        """
        if self._engine is None:
            raise BackendError(self.name, "no model loaded — call load_model() first")

        try:
            from vllm import SamplingParams
        except ImportError as exc:
            raise BackendError(self.name, "vllm is not installed", exc) from exc

        try:
            params = SamplingParams(max_tokens=max_tokens)
            outputs = self._engine.generate([prompt], params)  # type: ignore[union-attr]
        except Exception as exc:
            raise BackendError(self.name, "streaming generation failed", exc) from exc

        output = outputs[0]
        if output.outputs:
            # Yield individual token text pieces. vLLM stores per-token logprobs;
            # fall back to yielding the complete text if token-level data is absent.
            generated = output.outputs[0]
            if hasattr(generated, "token_ids") and hasattr(self._engine, "get_tokenizer"):
                try:
                    tokenizer = self._engine.get_tokenizer()  # type: ignore[union-attr]
                    for tid in generated.token_ids:
                        yield tokenizer.decode([tid])
                    return
                except Exception:
                    pass
            # Fallback: yield the whole text as one chunk.
            yield generated.text

    def unload_model(self) -> None:
        """Destroy the vLLM engine and reclaim memory."""
        self._engine = None
        self._model_id = None
        gc.collect()

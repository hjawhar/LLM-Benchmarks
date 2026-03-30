"""Timing and resource-usage measurement utilities.

All wall-clock measurements use `time.perf_counter_ns()` for nanosecond precision.
"""

from __future__ import annotations

import time
from types import TracebackType
from typing import Self

import psutil

from llm_bench.models import TimingMetrics

# ---------------------------------------------------------------------------
# Timer context manager
# ---------------------------------------------------------------------------


class Timer:
    """Context manager that records wall-clock elapsed time via perf_counter_ns."""

    def __init__(self) -> None:
        self._start_ns: int = 0
        self._end_ns: int = 0

    def __enter__(self) -> Self:
        self._start_ns = time.perf_counter_ns()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._end_ns = time.perf_counter_ns()

    @property
    def elapsed_ns(self) -> int:
        """Elapsed nanoseconds."""
        return self._end_ns - self._start_ns

    @property
    def elapsed_ms(self) -> float:
        """Elapsed milliseconds."""
        return self.elapsed_ns / 1_000_000

    @property
    def elapsed_s(self) -> float:
        """Elapsed seconds."""
        return self.elapsed_ns / 1_000_000_000


# ---------------------------------------------------------------------------
# Memory helper
# ---------------------------------------------------------------------------


def measure_memory(pid: int | None = None) -> float:
    """Return peak RSS of *pid* (default: current process) in MB."""
    proc = psutil.Process(pid)
    mem_info = proc.memory_info()
    return mem_info.rss / (1024 * 1024)


# ---------------------------------------------------------------------------
# MetricsCollector – accumulates timing data across a single generation run
# ---------------------------------------------------------------------------


class MetricsCollector:
    """Accumulates fine-grained timing data for a single generation run.

    Typical call order::

        collector.start_model_load()
        # … load model …
        collector.end_model_load()
        collector.start_generation()
        for token in stream:
            if first:
                collector.record_first_token()
            collector.record_token()
        collector.end_generation()
        metrics = collector.collect()
    """

    def __init__(self) -> None:
        self.reset()

    # -- model load ----------------------------------------------------------

    def start_model_load(self) -> None:
        """Mark the beginning of model loading."""
        self._model_load_start_ns = time.perf_counter_ns()

    def end_model_load(self) -> None:
        """Mark the end of model loading."""
        self._model_load_end_ns = time.perf_counter_ns()

    # -- generation ----------------------------------------------------------

    def start_generation(self) -> None:
        """Mark the start of the generation (prompt submitted)."""
        self._gen_start_ns = time.perf_counter_ns()

    def record_first_token(self) -> None:
        """Mark the instant the first token arrives."""
        if self._first_token_ns == 0:
            self._first_token_ns = time.perf_counter_ns()

    def record_token(self) -> None:
        """Increment the generated-token counter."""
        self._token_count += 1

    def end_generation(self) -> None:
        """Mark the end of generation."""
        self._gen_end_ns = time.perf_counter_ns()

    # -- collect -------------------------------------------------------------

    def collect(self) -> TimingMetrics:
        """Compute and return all timing metrics from the recorded data.

        If first-token was never recorded (e.g. backend error) TTFT is reported
        as the full generation duration so downstream consumers always get a
        finite, non-negative value rather than a sentinel.
        """
        model_load_s = self._ns_to_s(self._model_load_end_ns - self._model_load_start_ns)

        gen_duration_ns = self._gen_end_ns - self._gen_start_ns
        gen_duration_s = self._ns_to_s(gen_duration_ns)

        # TTFT: fall back to full generation duration when first token was never recorded.
        if self._first_token_ns != 0:
            ttft_ms = (self._first_token_ns - self._gen_start_ns) / 1_000_000
        else:
            ttft_ms = gen_duration_ns / 1_000_000

        # TPS: tokens generated / generation wall-clock time.
        tps = self._token_count / gen_duration_s if gen_duration_s > 0 else 0.0

        # Prompt eval speed: use time-to-first-token as a proxy for prompt
        # evaluation time.  The first token boundary approximates when prompt
        # processing finishes and decoding begins.
        prompt_eval_ns = (
            (self._first_token_ns - self._gen_start_ns)
            if self._first_token_ns != 0
            else gen_duration_ns
        )
        prompt_eval_s = self._ns_to_s(prompt_eval_ns)
        # We don't know the prompt-token count here; report inverse time (1/s)
        # so callers with the prompt length can derive tok/s.  The runner layer
        # may override this with a backend-reported value.
        prompt_eval_tps = 1.0 / prompt_eval_s if prompt_eval_s > 0 else 0.0

        peak_mem_mb = measure_memory()

        return TimingMetrics(
            ttft_ms=ttft_ms,
            tps=tps,
            prompt_eval_tps=prompt_eval_tps,
            model_load_time_s=model_load_s,
            peak_memory_mb=peak_mem_mb,
            total_duration_s=model_load_s + gen_duration_s,
        )

    # -- reset ---------------------------------------------------------------

    def reset(self) -> None:
        """Clear all recorded state for the next run."""
        self._model_load_start_ns: int = 0
        self._model_load_end_ns: int = 0
        self._gen_start_ns: int = 0
        self._gen_end_ns: int = 0
        self._first_token_ns: int = 0
        self._token_count: int = 0

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _ns_to_s(ns: int) -> float:
        return ns / 1_000_000_000

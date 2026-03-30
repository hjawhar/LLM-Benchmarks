from __future__ import annotations

import time

from llm_bench.metrics import MetricsCollector, Timer, measure_memory


class TestTimer:
    """Timer context manager records elapsed time."""

    def test_elapsed_positive(self) -> None:
        timer = Timer()
        with timer:
            # Even a no-op iteration should register > 0 ns via perf_counter_ns
            _ = sum(range(100))
        assert timer.elapsed_ns > 0

    def test_elapsed_seconds(self) -> None:
        timer = Timer()
        with timer:
            time.sleep(0.01)
        assert timer.elapsed_s >= 0.005  # conservative lower bound

    def test_elapsed_ms(self) -> None:
        timer = Timer()
        with timer:
            time.sleep(0.01)
        assert timer.elapsed_ms >= 5.0


class TestMetricsCollector:
    """Full lifecycle of MetricsCollector."""

    def test_full_lifecycle(self) -> None:
        mc = MetricsCollector()

        # Phase 1: model loading
        mc.start_model_load()
        _ = sum(range(1000))
        mc.end_model_load()

        # Phase 2: generation
        mc.start_generation()
        mc.record_first_token()
        mc.record_tokens(50)
        mc.end_generation()

        metrics = mc.collect()

        assert metrics.model_load_time_s >= 0
        assert metrics.ttft_ms >= 0
        assert metrics.tps > 0
        assert metrics.total_duration_s >= 0
        assert metrics.peak_memory_mb >= 0

    def test_reset_clears_state(self) -> None:
        mc = MetricsCollector()
        mc.start_model_load()
        mc.end_model_load()
        mc.start_generation()
        mc.record_first_token()
        mc.record_tokens(10)
        mc.end_generation()

        mc.reset()

        # After reset, collecting should fail or return zeroed/default metrics.
        # The exact behavior depends on implementation — we verify the collector
        # can be reused cleanly after reset.
        mc.start_model_load()
        mc.end_model_load()
        mc.start_generation()
        mc.record_first_token()
        mc.record_tokens(20)
        mc.end_generation()

        metrics = mc.collect()
        assert metrics.tps > 0


class TestMeasureMemory:
    """measure_memory returns a positive float (MB)."""

    def test_returns_positive(self) -> None:
        mem = measure_memory()
        assert isinstance(mem, float)
        assert mem > 0

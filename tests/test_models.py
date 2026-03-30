from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from llm_bench.models import (
    BackendConfig,
    BenchmarkConfig,
    BenchmarkResult,
    PromptConfig,
    QualityMetrics,
    TimingMetrics,
)


class TestBenchmarkConfig:
    """Validate BenchmarkConfig construction and rejection rules."""

    def test_valid_config(self, sample_config: BenchmarkConfig) -> None:
        assert len(sample_config.backends) == 1
        assert sample_config.backends[0].name == "ollama"

    def test_rejects_empty_backends(self) -> None:
        with pytest.raises(ValidationError):
            BenchmarkConfig(
                backends=[],
                prompts=[PromptConfig(builtin="short_qa")],
            )

    def test_rejects_missing_backends(self) -> None:
        with pytest.raises(ValidationError):
            BenchmarkConfig(
                prompts=[PromptConfig(builtin="short_qa")],
            )


class TestTimingMetrics:
    """Verify TimingMetrics serialization round-trip."""

    def test_round_trip(self, sample_timing: TimingMetrics) -> None:
        data = sample_timing.model_dump()
        restored = TimingMetrics.model_validate(data)
        assert restored == sample_timing

    def test_json_round_trip(self, sample_timing: TimingMetrics) -> None:
        json_str = sample_timing.model_dump_json()
        restored = TimingMetrics.model_validate_json(json_str)
        assert restored == sample_timing

    def test_fields_present(self, sample_timing: TimingMetrics) -> None:
        data = sample_timing.model_dump()
        expected_keys = {
            "ttft_ms",
            "tps",
            "prompt_eval_tps",
            "model_load_time_s",
            "peak_memory_mb",
            "total_duration_s",
        }
        assert expected_keys <= set(data.keys())


class TestBenchmarkResult:
    """BenchmarkResult with and without quality metrics."""

    def test_with_quality(self, sample_result: BenchmarkResult) -> None:
        assert sample_result.quality is not None
        assert sample_result.quality.perplexity == pytest.approx(8.2)
        assert sample_result.quality.task_accuracy == pytest.approx(0.95)

    def test_without_quality(self, sample_timing: TimingMetrics) -> None:
        result = BenchmarkResult(
            backend="mlx-lm",
            model="mlx-community/Llama-3.2-3B-Instruct-4bit",
            prompt="Hello",
            output="Hi there!",
            timing=sample_timing,
            quality=None,
            timestamp=datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc),
            run_index=0,
            config_hash="def456",
        )
        assert result.quality is None
        assert result.backend == "mlx-lm"

    def test_result_json_round_trip(self, sample_result: BenchmarkResult) -> None:
        json_str = sample_result.model_dump_json()
        restored = BenchmarkResult.model_validate_json(json_str)
        assert restored.backend == sample_result.backend
        assert restored.timing == sample_result.timing

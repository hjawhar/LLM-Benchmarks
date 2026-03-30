from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from llm_bench.models import (
    BackendConfig,
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkSettings,
    PromptConfig,
    QualityMetrics,
    TimingMetrics,
)
from llm_bench.storage import ResultsDB


@pytest.fixture()
def tmp_db(tmp_path: Path) -> ResultsDB:
    """Yield a ResultsDB connected to a temporary SQLite file, closed after use."""
    db_path = tmp_path / "test_results.db"
    db = ResultsDB(db_path)
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def sample_config() -> BenchmarkConfig:
    """Return a minimal valid BenchmarkConfig."""
    return BenchmarkConfig(
        backends=[
            BackendConfig(
                name="ollama",
                models=["llama3.2:3b"],
            ),
        ],
        prompts=[PromptConfig(builtin="short_qa")],
        settings={
            "max_tokens": 128,
            "runs_per_config": 1,
            "warmup_runs": 0,
            "cool_down_seconds": 0,
        },
    )


@pytest.fixture()
def sample_timing() -> TimingMetrics:
    """Return a TimingMetrics with realistic values."""
    return TimingMetrics(
        ttft_ms=42.5,
        tps=65.3,
        prompt_eval_tps=320.0,
        model_load_time_s=1.85,
        peak_memory_mb=2048.0,
        total_duration_s=3.72,
    )


@pytest.fixture()
def sample_result(sample_timing: TimingMetrics) -> BenchmarkResult:
    """Return a BenchmarkResult with realistic dummy data."""
    return BenchmarkResult(
        backend_name="ollama",
        model_id="llama3.2:3b",
        prompt_name="general_knowledge",
        prompt_text="What is the capital of France?",
        output_text="The capital of France is Paris.",
        timing=sample_timing,
        quality=QualityMetrics(perplexity=8.2, task_accuracy=0.95),
        timestamp=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
        run_index=0,
        settings=BenchmarkSettings(),
    )

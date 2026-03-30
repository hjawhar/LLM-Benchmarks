"""Pydantic v2 data models for benchmark configuration and results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, model_validator


class BackendConfig(BaseModel):
    """Configuration for a single inference backend."""

    name: str
    models: list[str]
    options: dict[str, object] = {}


class PromptConfig(BaseModel):
    """A prompt source: either a built-in name or custom text. Exactly one must be set."""

    builtin: str | None = None
    custom: str | None = None

    @model_validator(mode="after")
    def _one_must_be_set(self) -> PromptConfig:
        if self.builtin is None and self.custom is None:
            raise ValueError("Either 'builtin' or 'custom' must be set")
        if self.builtin is not None and self.custom is not None:
            raise ValueError("Only one of 'builtin' or 'custom' may be set, not both")
        return self


class BenchmarkSettings(BaseModel):
    """Tuning knobs for benchmark execution."""

    max_tokens: int = 512
    runs_per_config: int = 3
    warmup_runs: int = 1
    cool_down_seconds: float = 5.0


class BenchmarkConfig(BaseModel):
    """Top-level benchmark configuration loaded from YAML."""

    backends: list[BackendConfig]
    prompts: list[PromptConfig]
    settings: BenchmarkSettings = BenchmarkSettings()

    @model_validator(mode="after")
    def _must_have_entries(self) -> BenchmarkConfig:
        if not self.backends:
            raise ValueError("At least one backend must be specified")
        if not self.prompts:
            raise ValueError("At least one prompt must be specified")
        return self


class TimingMetrics(BaseModel):
    """Raw timing measurements for a single generation run."""

    ttft_ms: float
    tps: float
    prompt_eval_tps: float
    model_load_time_s: float
    peak_memory_mb: float
    total_duration_s: float


class QualityMetrics(BaseModel):
    """Optional quality-evaluation scores."""

    perplexity: float | None = None
    task_accuracy: float | None = None


class BenchmarkResult(BaseModel):
    """Complete record of one benchmark execution."""

    backend_name: str
    model_id: str
    prompt_name: str
    prompt_text: str
    output_text: str
    timing: TimingMetrics
    quality: QualityMetrics | None = None
    run_index: int
    timestamp: datetime
    settings: BenchmarkSettings

# LLM Inference Benchmark Suite - Design Specification

**Date:** 2026-03-30
**Status:** Draft
**Platform:** Apple Silicon (M4 Max, 48 GB unified memory)

---

## 1. Overview

`llm_bench` is a benchmarking tool for comparing LLM inference backends on Apple Silicon. It measures latency, throughput, memory, and output quality across backends under identical conditions (same model, same prompts, same hardware).

**Goals:**
- Reproducible, statistically sound comparisons between inference backends.
- Single CLI entry point for running benchmarks, viewing results, and generating reports.
- Extensible plugin system so new backends can be added without modifying core code.
- Persistent storage of all results for longitudinal analysis.

**Non-goals:**
- Training or fine-tuning benchmarks.
- Multi-node / distributed inference.
- Linux GPU (CUDA/ROCm) support (Apple Silicon only).

---

## 2. Target Platform

| Property | Value |
|----------|-------|
| Chip | Apple M4 Max |
| Unified Memory | 48 GB |
| OS | macOS 15+ |
| Python | 3.11+ |
| Package Manager | uv |

Unified memory is shared between CPU and GPU on Apple Silicon. Peak memory is measured via `psutil` process RSS, which captures the combined allocation visible to the OS.

---

## 3. Supported Backends

| Backend | Python Package | Inference Style | Notes |
|---------|---------------|-----------------|-------|
| **mlx-lm** | `mlx-lm` | Native Metal via MLX | Apple's first-party ML framework |
| **Ollama** | `ollama` | HTTP API to local server | Requires `ollama` daemon running |
| **llama.cpp** | `llama-cpp-python` | C++ bindings with Metal | Quantized GGUF models |
| **vLLM** | `vllm` (Metal fork) | PagedAttention engine | Experimental Apple Silicon support |

Each backend is optional. If its package is not installed, `is_available()` returns `False` and the runner skips it with a warning.

---

## 4. Architecture

```
CLI (Click)
  |
  v
BenchmarkRunner
  |-- loads config (YAML)
  |-- resolves backends (plugin registry)
  |-- for each (backend, model, prompt_set):
  |       |
  |       v
  |     Backend.load_model()
  |     Backend.generate()  -->  MetricsCollector
  |     Backend.unload_model()
  |       |
  |       v
  |     MetricsCollector.finalize()
  |
  v
Storage (SQLite)
  |
  v
Reporter (Rich tables / Plotly HTML)
```

### Plugin-Based Backend System

Backends implement a `Backend` protocol. Discovery is explicit: a registry maps string keys (`"mlx-lm"`, `"ollama"`, etc.) to concrete classes. No metaclass magic, no entry points.

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from llm_bench.models import GenerateRequest, GenerateResponse, ModelInfo


@runtime_checkable
class Backend(Protocol):
    """Contract every inference backend must satisfy."""

    @property
    def name(self) -> str:
        """Unique backend identifier, e.g. 'mlx-lm'."""
        ...

    def is_available(self) -> bool:
        """Return True if the backend's dependencies are installed."""
        ...

    def load_model(self, model_id: str, **kwargs: object) -> ModelInfo:
        """Load a model into memory. Return metadata about what was loaded."""
        ...

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Run inference. Populate timing fields in the response."""
        ...

    def unload_model(self) -> None:
        """Release model from memory."""
        ...
```

All timing is done with `time.perf_counter_ns()` inside each backend's `generate()` method to capture TTFT and per-token timing at the source.

---

## 5. Core Metrics

| Metric | Unit | How Measured |
|--------|------|-------------|
| **Time to First Token (TTFT)** | ms | `perf_counter_ns` delta from generate call to first token yield |
| **Tokens Per Second (TPS)** | tok/s | `output_tokens / generation_time` |
| **Prompt Eval Speed** | tok/s | `prompt_tokens / prompt_eval_time` |
| **Model Load Time** | s | `perf_counter_ns` delta around `load_model()` |
| **Peak Memory Usage** | MB | `psutil.Process().memory_info().rss` high-water mark during generation |
| **Total Duration** | s | Wall clock from `load_model()` through `generate()` completion |
| **Output Quality** | float [0,1] | Optional. Perplexity-based or task-accuracy score |

All timing uses nanosecond precision (`time.perf_counter_ns()`), stored as integers, converted to human units only at display time.

---

## 6. Data Flow

```
                  config.yaml
                      |
                      v
  CLI  ──────>  BenchmarkRunner
  (click)            |
                     |  iterates over (backend, model, prompt_set, run_index)
                     v
               Backend.generate()
                     |
                     |  raw timing + output text
                     v
              MetricsCollector
                     |
                     |  BenchmarkResult (pydantic model)
                     v
              Storage (SQLite)
                     |
                     v
               Reporter
              /          \
    Rich table (CLI)    Plotly HTML (static)
```

- **Runner** owns the outer loop: warmup runs, timed runs, cooldown pauses.
- **MetricsCollector** owns memory sampling (background thread polling RSS).
- **Storage** appends results row-by-row; never updates or deletes.
- **Reporter** reads from storage; it never touches backends or the runner.

---

## 7. Configuration

Config is a single YAML file. All fields have defaults; a minimal config needs only `models`.

```yaml
# bench_config.yaml

models:
  - id: "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
    backends: ["mlx-lm", "llama.cpp"]
    params:
      max_tokens: 512
      temperature: 0.0

  - id: "ollama/mistral:7b"
    backends: ["ollama"]
    params:
      max_tokens: 512
      temperature: 0.0

prompt_sets:
  - "short_qa"
  - "code_completion"

runs_per_config: 5        # timed runs per (backend, model, prompt_set)
warmup_runs: 1            # discarded runs before timing starts
cooldown_seconds: 2       # pause between runs to let thermals settle

quality:
  enabled: false          # set true or use --quality flag
  metrics: ["perplexity"] # "perplexity", "task_accuracy"

output:
  db_path: "results/benchmarks.db"
  html_dir: "results/charts"
```

Pydantic v2 models validate the config at load time. Unknown keys raise, missing required fields raise with a clear message.

---

## 8. Storage

SQLite via the stdlib `sqlite3` module. One database, two core tables:

```sql
CREATE TABLE runs (
    id            TEXT PRIMARY KEY,  -- uuid4
    timestamp     TEXT NOT NULL,     -- ISO 8601
    config_hash   TEXT NOT NULL,     -- SHA256 of the YAML config
    backend       TEXT NOT NULL,
    model_id      TEXT NOT NULL,
    prompt_set    TEXT NOT NULL,
    prompt_index  INTEGER NOT NULL,
    run_index     INTEGER NOT NULL,
    is_warmup     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE metrics (
    run_id              TEXT NOT NULL REFERENCES runs(id),
    ttft_ns             INTEGER,
    tps                 REAL,
    prompt_eval_tps     REAL,
    model_load_time_ns  INTEGER,
    peak_memory_bytes   INTEGER,
    total_duration_ns   INTEGER,
    quality_score       REAL,
    output_token_count  INTEGER,
    prompt_token_count  INTEGER
);
```

Raw nanosecond / byte values in storage; human-friendly units only at report time.

---

## 9. Reporting

### CLI Tables (Rich)

```
$ llm-bench report --last

Backend     Model              TTFT (ms)  TPS    Mem (MB)  Quality
----------  -----------------  ---------  -----  --------  -------
mlx-lm      Mistral-7B-4bit      42.3    68.1     4120      --
llama.cpp   Mistral-7B-Q4_K_M    55.7    51.4     3890      --
ollama      mistral:7b            61.2    47.9     4300      --
```

Displays mean +/- stddev when `runs_per_config > 1`.

### Plotly HTML (Static)

Generated as self-contained `.html` files suitable for GitHub Pages:
- Grouped bar chart: TPS by backend per model.
- Box plots: TTFT distribution per backend.
- Memory timeline: peak RSS over prompt set.

---

## 10. Quality Evaluation

Enabled via `--quality` CLI flag or `quality.enabled: true` in config.

### Perplexity

Computed by backends that expose log-probabilities. The quality evaluator passes a reference corpus, collects per-token log-probs, and computes perplexity. Backends that do not support log-probs report `quality_score: null`.

### Task Accuracy

For structured prompt sets (e.g., `short_qa` with expected answers), outputs are compared against reference answers using exact-match or fuzzy-match scoring.

Both metrics are optional per-run. They add overhead and are off by default.

---

## 11. Prompt Sets

Built-in sets ship as YAML files under `llm_bench/prompts/`:

| Set | Purpose | Typical Length |
|-----|---------|----------------|
| `short_qa` | Factual Q&A, tests TTFT and short generation | 10-50 tokens out |
| `long_generation` | Essay / story generation, tests sustained TPS | 500-2000 tokens out |
| `code_completion` | Function completion, tests structured output | 100-500 tokens out |
| `summarization` | Condense long input, tests prompt eval speed | 50-200 tokens out |

Each prompt file:

```yaml
# prompts/short_qa.yaml
name: short_qa
description: "Short factual question-answering"
prompts:
  - text: "What is the capital of France?"
    expected: "Paris"
    max_tokens: 32
  - text: "Explain Newton's first law in one sentence."
    expected: null
    max_tokens: 64
```

Custom prompt sets can be added to the config by path.

---

## 12. Statistical Reliability

- **`warmup_runs`**: Discarded runs that prime caches and GPU state. Default: 1.
- **`runs_per_config`**: Timed runs whose metrics are recorded. Default: 5.
- **`cooldown_seconds`**: Sleep between runs to reduce thermal throttling variance. Default: 2.
- Reports show mean, median, stddev, min, max for each metric.
- Outlier flagging: runs where any metric deviates > 2 stddev from the mean are flagged but not discarded.

---

## 13. Tooling

| Tool | Role |
|------|------|
| **Python 3.11+** | Runtime |
| **uv** | Package management, virtualenv |
| **Click** | CLI framework |
| **Pydantic v2** | Config + data model validation |
| **PyYAML** | Config parsing |
| **Rich** | CLI table output |
| **Plotly** | Static HTML chart generation |
| **psutil** | Memory measurement |
| **pytest** | Testing |
| **ruff** | Linting + formatting |

Dev dependencies (pytest, ruff) are separated in `pyproject.toml` under `[project.optional-dependencies]`.

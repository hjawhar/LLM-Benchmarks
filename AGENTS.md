# Repository Guidelines

## Project Overview

LLM-Benchmarks (`llm-bench`) is a Python benchmarking harness for comparing LLM inference backends on Apple Silicon. It measures throughput, latency, memory usage, model load time, and optionally output quality across mlx-lm, ollama, llama.cpp, and vLLM backends.

Target platform: macOS on Apple Silicon (M4 Max, 48GB unified memory).

## Architecture & Data Flow

Pipeline architecture with plugin-based backends:

```
CLI (Click) -> Config (YAML/Pydantic) -> BenchmarkRunner -> Backend (Protocol)
                                              |
                                        MetricsCollector
                                              |
                                     ResultsDB (SQLite)
                                              |
                                    Reporter (Rich / Plotly HTML)
```

### Key Flow

1. `cli.py` parses args, loads YAML config via `config.py` into Pydantic models
2. `BenchmarkRunner` resolves available backends via lazy-import registry
3. For each (backend x model x prompt x run), the runner:
   - Loads the model (timed separately)
   - Runs warmup iterations (discarded)
   - Runs timed iterations via `run_single()`
   - Collects metrics via `MetricsCollector`
   - Persists each `BenchmarkResult` to SQLite
   - Sleeps `cool_down_seconds` between runs
4. Results are displayed as Rich CLI tables and/or Plotly static HTML

### Backend Plugin System

Backends use `typing.Protocol` (structural subtyping, not inheritance). Each backend is a standalone class that satisfies the `Backend` protocol shape. Dependencies are imported lazily inside methods so the registry can load without requiring all libraries installed.

Two backend registries exist (known inconsistency — see Known Issues):
- `llm_bench/backends/__init__.py`: dict mapping name -> class, with `get_backend()`, `list_backends()`, `get_available_backends()`
- `llm_bench/runner.py`: separate `_BACKEND_REGISTRY` dict mapping name -> dotted import path, with `_import_backend()` loader

## Key Directories

```
llm_bench/              # Main package
  backends/             # Backend implementations (one file per backend)
  prompts/              # Built-in prompt sets (YAML) and loader
  quality/              # Quality evaluation (perplexity stub, task accuracy)
configs/                # User-facing YAML benchmark configs
tests/                  # pytest test suite
  test_backends/        # Backend registry tests
docs/specs/             # Design specifications
benchmarks/             # Runtime output (SQLite DB, HTML reports) — gitignored
```

## Development Commands

```bash
# Package manager: uv (required)
# Runtime: Python 3.11+ (pyenv)

# Install dependencies
uv sync                         # Core deps only
uv sync --extra dev             # + pytest, ruff, pytest-cov
uv sync --extra mlx             # + mlx-lm
uv sync --extra ollama          # + ollama client
uv sync --extra llamacpp        # + llama-cpp-python
uv sync --extra all             # mlx + ollama + llamacpp (no vllm — unstable on macOS)

# Run benchmarks
uv run llm-bench run --config configs/benchmark.yaml
uv run llm-bench run --quality                        # Enable quality evaluation
uv run llm-bench run --output-dir benchmarks/reports   # Custom report output

# Generate reports from existing results
uv run llm-bench report --db benchmarks/results.db --format both

# List backends and their availability
uv run llm-bench backends

# Run tests
uv run pytest                   # All tests
uv run pytest tests/test_models.py  # Single module
uv run pytest -x               # Stop on first failure

# Lint
uv run ruff check llm_bench/ tests/
uv run ruff format --check llm_bench/ tests/
```

## Code Conventions & Common Patterns

### Language & Style
- `from __future__ import annotations` in every `.py` file
- Type hints on all function signatures and class attributes
- Ruff for linting/formatting: line length 100, Python 3.11 target
- Rules: `E, F, I, N, W, UP` (pyflakes, isort, naming, pyupgrade)

### Data Models
- All data structures are **Pydantic v2 `BaseModel`** subclasses in `llm_bench/models.py`
- Validation via `@model_validator(mode="after")` for cross-field constraints
- `TimingMetrics`, `QualityMetrics`, `BenchmarkResult` are the canonical record types
- Config models: `BenchmarkConfig`, `BackendConfig`, `PromptConfig`, `BenchmarkSettings`

### Error Handling
- `BackendError(backend_name, message, cause)` wraps all backend-specific exceptions with context
- `BackendError` chains the original exception via `__cause__`
- Backends: `is_available()` must never raise — returns `False` on any failure
- Runner: catches and logs exceptions at every level (import, load, generate), skips and continues

### Timing
- All timing uses `time.perf_counter_ns()` for nanosecond precision
- `Timer` context manager for simple elapsed-time measurement
- `MetricsCollector` for structured generation lifecycle: `start_model_load` -> `end_model_load` -> `start_generation` -> `record_first_token` -> `record_token` (repeated) -> `end_generation` -> `collect()`
- Memory via `psutil.Process.memory_info().rss`

### Backend Implementation Pattern
Every backend follows this structure:
```python
class SomeBackend:
    name: str = "backend-name"       # Class-level, matches registry key

    def is_available(self) -> bool:
        try:
            import the_library       # Lazy import
            return True
        except ImportError:
            return False

    def load_model(self, model_id: str, **kwargs) -> None:
        import the_library            # Lazy import again
        self._model = the_library.load(model_id)

    def generate(self, prompt: str, max_tokens: int) -> tuple[str, TimingMetrics | None]:
        # Use the library's API, wrap errors in BackendError
        ...

    def unload_model(self) -> None:
        self._model = None
        gc.collect()
```

### Config Pattern
YAML config files are loaded and validated against Pydantic models:
```python
data = yaml.safe_load(path.read_text())
config = BenchmarkConfig.model_validate(data)
```

## Important Files

| File | Role |
|------|------|
| `llm_bench/cli.py` | Click CLI entry point (`cli` group) — registered as `llm-bench` console script |
| `llm_bench/models.py` | All Pydantic data models — the single source of truth for data shapes |
| `llm_bench/runner.py` | `BenchmarkRunner` orchestration + Backend Protocol (duplicate) + built-in prompt catalogue + backend registry (lazy import map) |
| `llm_bench/backends/base.py` | Canonical `Backend` Protocol definition + `BackendError` |
| `llm_bench/backends/__init__.py` | Backend registry (dict mapping name -> class) |
| `llm_bench/metrics.py` | `Timer`, `MetricsCollector`, `measure_memory()` |
| `llm_bench/storage.py` | `ResultsDB` — SQLite with WAL mode, context manager |
| `llm_bench/report.py` | `CLIReporter` (Rich tables), `HTMLReporter` (Plotly charts) |
| `llm_bench/config.py` | `load_config()` — YAML to `BenchmarkConfig` |
| `llm_bench/prompts/default.yaml` | Built-in prompt sets (4 categories, 11 prompts) |
| `configs/benchmark.yaml` | Default user-facing benchmark configuration |
| `docs/specs/2026-03-30-llm-benchmarks-design.md` | Design specification |

## Runtime & Tooling

| Tool | Version | Purpose |
|------|---------|---------|
| Python | >= 3.11 | Runtime (managed via pyenv) |
| uv | latest | Package manager, virtualenv, script runner |
| hatchling | — | Build backend (`pyproject.toml`) |
| ruff | >= 0.8 | Linter + formatter |
| pytest | >= 8.0 | Test runner |

### Backend Dependencies (optional extras)
| Extra | Package | Backend |
|-------|---------|---------|
| `mlx` | `mlx-lm >= 0.19` | MLX-LM (Apple Silicon native) |
| `ollama` | `ollama >= 0.4` | Ollama (requires running server at localhost:11434) |
| `llamacpp` | `llama-cpp-python >= 0.3` | llama.cpp (model_id is a GGUF file path) |
| `vllm` | `vllm-metal >= 0.1` | vLLM via Metal plugin (experimental on macOS) |

## Testing

- Framework: **pytest** with fixtures in `tests/conftest.py`
- Test paths: `tests/` (configured in `pyproject.toml`)
- Run flags: `-v --tb=short` (default via `addopts`)
- Coverage: `pytest-cov` available via `dev` extra

### Shared Fixtures (`tests/conftest.py`)
| Fixture | Returns | Purpose |
|---------|---------|---------|
| `tmp_db` | `ResultsDB` | Temp SQLite database, auto-closed |
| `sample_config` | `BenchmarkConfig` | Minimal valid config (1 backend, 1 prompt) |
| `sample_timing` | `TimingMetrics` | Realistic timing values |
| `sample_result` | `BenchmarkResult` | Full result with quality metrics |

### Test Files
| File | Covers |
|------|--------|
| `tests/test_models.py` | Pydantic model validation, serialization round-trips |
| `tests/test_metrics.py` | Timer, MetricsCollector lifecycle, measure_memory |
| `tests/test_storage.py` | SQLite save/retrieve, filters, WAL mode, context manager |
| `tests/test_config.py` | YAML loading, missing file, invalid config |
| `tests/test_runner.py` | Prompt resolution, unavailable backend skipping |
| `tests/test_backends/test_registry.py` | Registry functions, protocol method presence |

### Testing Principles
- No mocks of actual backend libraries — test the registry and availability checks only
- Storage tests use `tmp_path` fixture for isolated SQLite files
- Config tests write temp YAML files and validate through the real loader

## Known Issues (Scaffold-Stage)

These are integration issues from the initial scaffold that need resolution:

1. **Duplicate Backend Protocol**: `runner.py` defines its own `Backend` protocol (with `generate() -> str`) that diverges from `backends/base.py` (with `generate() -> tuple[str, TimingMetrics | None]`). The canonical definition is in `backends/base.py`.

2. **Duplicate Backend Registry**: `runner.py` has `_BACKEND_REGISTRY` with wrong module paths (e.g., `llm_bench.backends.mlx_backend.MlxBackend`). The working registry is in `backends/__init__.py` with correct class references.

3. **CLI API Mismatches**: `cli.py` references APIs that don't match the actual modules — `ResultStore` vs `ResultsDB`, `r.metrics` vs `r.timing`, `get_registry()` vs module-level functions. These need alignment.

4. **TimingMetrics Construction Bug**: All 4 backends pass extra fields (`output_tokens`, `prompt_tokens`) and `None` for non-optional float fields to `TimingMetrics`. Pydantic will reject these at runtime.

5. **Runner TPS Bug**: `run_single()` iterates characters of output string (`for _ in output`), counting characters as tokens. TPS metric will report characters/second, not tokens/second.

6. **Storage Round-Trip Loss**: `ResultsDB._row_to_result()` reconstructs `BenchmarkSettings` with only `max_tokens` and `runs_per_config`, losing `warmup_runs` and `cool_down_seconds`.

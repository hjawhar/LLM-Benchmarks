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
                                     ResultsDB (SQLite WAL)
                                              |
                                    Reporter (Rich CLI / Markdown)
```

### Key Flow

1. `cli.py` parses args, loads YAML config via `config.py` into Pydantic models
2. `BenchmarkRunner` resolves available backends via lazy-import registry
3. For each (backend x model x prompt x run), the runner:
   - Loads the model (timed separately via `MetricsCollector`)
   - Runs warmup iterations (discarded)
   - Runs timed iterations via `run_single()`
   - Persists each `BenchmarkResult` to SQLite
   - Sleeps `cool_down_seconds` between runs
4. Results are displayed as Rich CLI tables and written to `RESULTS.md`

### Backend Plugin System

Backends use `typing.Protocol` (structural subtyping, not inheritance). Each backend is a standalone class satisfying the `Backend` protocol shape. Dependencies are imported lazily inside methods so the registry can load without requiring all libraries installed.

The backend registry lives in `llm_bench/backends/__init__.py` — a dict mapping name to class with `get_backend()`, `list_backends()`, `get_available_backends()` accessors.

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
models/                 # GGUF model files (gitignored)
```

## Setup & Development Commands

### First-Time Setup

```bash
# Install uv (package manager) if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install core + dev dependencies
uv sync --extra dev

# Install with specific backend support
uv sync --extra dev --extra mlx       # + mlx-lm
uv sync --extra dev --extra ollama    # + ollama Python client
uv sync --extra dev --extra llamacpp  # + llama-cpp-python
uv sync --extra dev --extra all       # mlx + ollama + llamacpp
```

Note: The vLLM extra (`vllm-metal`) requires Python >= 3.12. If on 3.11, it is silently skipped.

### Running Tests

```bash
# Run full test suite (33 tests, ~0.1s)
uv run pytest

# Run a specific test module
uv run pytest tests/test_models.py
uv run pytest tests/test_storage.py
uv run pytest tests/test_metrics.py
uv run pytest tests/test_config.py
uv run pytest tests/test_runner.py
uv run pytest tests/test_backends/test_registry.py

# Run a single test by name
uv run pytest -k "test_full_lifecycle"

# Stop on first failure
uv run pytest -x

# With coverage
uv run pytest --cov=llm_bench
```

Default pytest flags (from `pyproject.toml`): `-v --tb=short`

### Linting & Formatting

```bash
# Check for lint errors
uv run ruff check llm_bench/ tests/

# Auto-fix lint errors
uv run ruff check --fix llm_bench/ tests/

# Check formatting
uv run ruff format --check llm_bench/ tests/

# Apply formatting
uv run ruff format llm_bench/ tests/
```

Ruff config: Python 3.11 target, line length 100, rules `E, F, I, N, W, UP`.

### Running Benchmarks

```bash
# Check which backends are available
uv run llm-bench backends

# Run benchmarks with default config
uv run llm-bench run

# Run with custom config
uv run llm-bench run --config path/to/config.yaml

# Run with quality evaluation enabled
uv run llm-bench run --quality

# Run with custom output directory
uv run llm-bench run --output-dir ./my-results

# Generate reports from existing results
# Run benchmarks (outputs RESULTS.md to project root)
uv run llm-bench run
```

### CLI Commands Reference

| Command | Description |
|---------|-------------|
| `llm-bench run` | Run benchmarks from config (default: `configs/benchmark.yaml`) |
| `llm-bench report` | Generate reports from existing SQLite results |
| `llm-bench backends` | List backends and their install status |
| `llm-bench --version` | Show version |

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
- `BackendError(backend_name, message, cause)` wraps all backend-specific exceptions
- Chains the original exception via `__cause__`
- `is_available()` must never raise -- returns `False` on any failure
- Runner catches and logs exceptions at every level (import, load, generate), skips and continues

### Timing
- All timing uses `time.perf_counter_ns()` for nanosecond precision
- `Timer` context manager for simple elapsed-time measurement
- `MetricsCollector` for structured generation lifecycle:
  ```
  start_model_load -> end_model_load ->
  start_generation -> record_first_token -> record_token (repeated) ->
  end_generation -> collect()
  ```
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
        import the_library
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
| `llm_bench/cli.py` | Click CLI entry point (`cli` group) -- registered as `llm-bench` console script |
| `llm_bench/models.py` | All Pydantic data models -- single source of truth for data shapes |
| `llm_bench/runner.py` | `BenchmarkRunner` orchestration + built-in prompt catalogue + lazy backend import registry |
| `llm_bench/backends/base.py` | Canonical `Backend` Protocol definition + `BackendError` |
| `llm_bench/backends/__init__.py` | Backend registry (dict mapping name -> class) |
| `llm_bench/metrics.py` | `Timer`, `MetricsCollector`, `measure_memory()` |
| `llm_bench/storage.py` | `ResultsDB` -- SQLite with WAL mode, context manager |
| `llm_bench/report.py` | `CLIReporter` (Rich tables), `MarkdownReporter` (GitHub markdown) |
| `llm_bench/config.py` | `load_config()` -- YAML to `BenchmarkConfig` |
| `llm_bench/prompts/default.yaml` | Built-in prompt sets (4 categories, 11 prompts) |
| `configs/benchmark.yaml` | Default user-facing benchmark configuration |

## Runtime & Tooling

| Tool | Version | Purpose |
|------|---------|---------|
| Python | >= 3.11 | Runtime (managed via pyenv) |
| uv | latest | Package manager, virtualenv, script runner |
| hatchling | -- | Build backend (`pyproject.toml`) |
| ruff | >= 0.8 | Linter + formatter |
| pytest | >= 8.0 | Test runner |

### Backend Dependencies (optional extras)

| Extra | Package | Backend | Notes |
|-------|---------|---------|-------|
| `mlx` | `mlx-lm >= 0.19` | MLX-LM | Apple Silicon native via MLX framework |
| `ollama` | `ollama >= 0.4` | Ollama | Requires running ollama server at localhost:11434 |
| `llamacpp` | `llama-cpp-python >= 0.3` | llama.cpp | model_id is a GGUF file path |
| `vllm` | `vllm-metal >= 0.1` | vLLM | Requires Python >= 3.12, experimental on macOS |

## Testing

- Framework: **pytest** with shared fixtures in `tests/conftest.py`
- Test paths: `tests/` (configured in `pyproject.toml`)
- Default flags: `-v --tb=short` (via `addopts`)
- Coverage: `pytest-cov` available via `dev` extra

### Shared Fixtures (`tests/conftest.py`)

| Fixture | Returns | Purpose |
|---------|---------|---------|
| `tmp_db` | `ResultsDB` | Temp SQLite database, auto-closed after test |
| `sample_config` | `BenchmarkConfig` | Minimal valid config (1 backend, 1 prompt) |
| `sample_timing` | `TimingMetrics` | Realistic timing values |
| `sample_result` | `BenchmarkResult` | Full result with quality metrics |

### Test Modules

| File | Covers |
|------|--------|
| `tests/test_models.py` | Pydantic model validation, serialization round-trips |
| `tests/test_metrics.py` | Timer, MetricsCollector lifecycle, measure_memory |
| `tests/test_storage.py` | SQLite save/retrieve, filters, WAL mode, context manager |
| `tests/test_config.py` | YAML loading, missing file, invalid config |
| `tests/test_runner.py` | Prompt resolution, unavailable backend skipping |
| `tests/test_backends/test_registry.py` | Registry functions, protocol method presence |

### Testing Principles
- No mocks of actual backend libraries -- test the registry and availability checks only
- Storage tests use `tmp_path` fixture for isolated SQLite files
- Config tests write temp YAML files and validate through the real loader
- Tests run without any backend installed (~0.1s total)

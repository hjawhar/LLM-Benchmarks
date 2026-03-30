# LLM Benchmarks

Benchmark suite for comparing LLM inference backends on Apple Silicon. Measures throughput, latency, memory usage, and model load time across real workloads.

## Hardware

| | |
|---|---|
| **Machine** | MacBook Pro, Apple M4 Max |
| **Memory** | 48 GB unified |
| **OS** | macOS |
| **Python** | 3.11 |

## Backends Tested

| Backend | Library | Version | Description |
|---------|---------|---------|-------------|
| **mlx-lm** | [mlx-lm](https://github.com/ml-explore/mlx-lm) | 0.31.1 | Apple's MLX framework, native Metal acceleration |
| **ollama** | [ollama](https://ollama.com) | 0.19.0 | Local inference server with REST API |
| **llama.cpp** | [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) | 0.3.19 | C++ inference engine via Python bindings |

## Models

All benchmarks use **Llama 3.2 3B Instruct** in comparable quantizations:

| Backend | Model ID | Quantization |
|---------|----------|-------------|
| mlx-lm | `mlx-community/Llama-3.2-3B-Instruct-4bit` | 4-bit |
| ollama | `llama3.2:3b` | Q4_K_M (default) |
| llama.cpp | `Llama-3.2-3B-Instruct-Q4_K_M.gguf` | Q4_K_M |

## Prompts

Each backend is tested against two prompt categories (3 runs per prompt, 1 warmup):

| Category | Prompts | Description |
|----------|---------|-------------|
| **short_qa** | general_knowledge, math_reasoning, definition | Short factual answers, 10-100 tokens output |
| **app_generation** | express_app | Generate a complete Node.js/Express.js CRUD REST API (~2048 tokens output) |

## Results

> 36 total runs (3 backends x 4 prompts x 3 runs), `max_tokens=2048`

### Summary

| Backend | Model | Runs | TTFT (ms) | TPS (tok/s) | Load (s) | Memory (MB) | Total (s) |
| ------- | ----- | ---: | --------: | ----------: | -------: | ----------: | --------: |
| mlx-lm | Llama-3.2-3B-Instruct-4bit | 12 | 5647.6 ± 5372.4 | 177.6 ± 15.3 | 1.1 ± 0.0 | 2116.5 ± 1.8 | 5.6 ± 5.4 |
| ollama | llama3.2:3b | 12 | 46.7 ± 25.7 | 162.2 ± 27.6 | 2.2 ± 0.0 | 2117.6 ± 0.0 | 2.6 ± 3.7 |
| llama.cpp | Llama-3.2-3B-Instruct-Q4_K_M | 12 | 6021.0 ± 9377.8 | 79.9 ± 11.8 | 1.3 ± 0.0 | 6258.5 ± 16.4 | 6.0 ± 9.4 |

### Express.js App Generation (long output)

| Backend | Run 1 | Run 2 | Run 3 | Avg TPS |
| ------- | ----: | ----: | ----: | ------: |
| mlx-lm | 188.5 tok/s | 184.8 tok/s | 187.0 tok/s | **186.8** |
| ollama | 113.4 tok/s | 123.8 tok/s | 119.6 tok/s | **118.9** |
| llama.cpp | 65.2 tok/s | 73.3 tok/s | 75.1 tok/s | **71.2** |

### Short QA (short output)

| Backend | general_knowledge | math_reasoning | definition | Avg TPS |
| ------- | ----------------: | -------------: | ---------: | ------: |
| mlx-lm | 193.2 tok/s | 173.6 tok/s | 156.9 tok/s | **174.6** |
| ollama | 190.4 tok/s | 168.6 tok/s | 170.6 tok/s | **176.5** |
| llama.cpp | 71.2 tok/s | 90.4 tok/s | 86.7 tok/s | **82.8** |

### Key Observations

- **mlx-lm** delivers the highest sustained throughput on long outputs (187 tok/s on Express.js generation), benefiting from native Metal acceleration.
- **ollama** has the best time-to-first-token (47ms vs 5.6s for mlx-lm) because it keeps models hot in its server process, making it ideal for interactive/chat use cases.
- **llama.cpp** via Python bindings runs at roughly half the speed of the other two. The Python wrapper overhead is documented upstream. Direct `llama.cpp` CLI would be faster.
- All three backends use comparable memory (~2.1 GB) except llama.cpp's Python bindings which report higher process RSS (~6.3 GB) due to the embedded C++ runtime.

## Quick Start

```bash
# Install
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --extra dev --extra mlx --extra ollama
pip install --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/metal llama-cpp-python

# Check available backends
uv run llm-bench backends

# Run benchmarks
uv run llm-bench run

# Generate reports from existing data
uv run llm-bench report
```

### Configuration

Edit `configs/benchmark.yaml` to customize:

```yaml
backends:
  - name: mlx-lm
    models:
      - mlx-community/Llama-3.2-3B-Instruct-4bit
  - name: ollama
    models:
      - llama3.2:3b
  - name: llama-cpp
    models:
      - models/Llama-3.2-3B-Instruct-Q4_K_M.gguf

prompts:
  - builtin: short_qa
  - builtin: app_generation

settings:
  max_tokens: 2048
  runs_per_config: 3
  warmup_runs: 1
  cool_down_seconds: 2.0
```

### Available Prompt Categories

| Category | Prompts | Typical Output |
|----------|---------|----------------|
| `short_qa` | general_knowledge, math_reasoning, definition | 10-100 tokens |
| `long_generation` | essay, story, explanation | 200-500 tokens |
| `code_completion` | python_function, algorithm, api_endpoint | 200-500 tokens |
| `summarization` | technical, concise | 50-150 tokens |
| `app_generation` | express_app (full Node.js/Express CRUD API) | 1000-2048 tokens |

### Output

Each run produces:
- **CLI table** in the terminal (via Rich)
- **`benchmarks/reports/RESULTS.md`** -- GitHub-formatted markdown tables
- **`benchmarks/reports/index.html`** -- interactive Plotly charts

## Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| **TTFT** | ms | Time to First Token -- latency before output begins |
| **TPS** | tok/s | Tokens Per Second -- generation throughput |
| **Load** | s | Model load time into memory |
| **Memory** | MB | Peak process RSS during inference |
| **Total** | s | End-to-end request time |

## Project Structure

```
llm_bench/              # Main package
  backends/             # mlx-lm, ollama, llama-cpp, vllm backends
  prompts/              # Built-in prompt sets (YAML)
  quality/              # Optional quality evaluation
  cli.py                # Click CLI (llm-bench command)
  runner.py             # Benchmark orchestration
  metrics.py            # Timing and memory measurement
  storage.py            # SQLite persistence
  report.py             # Rich, Plotly, and Markdown reporters
  models.py             # Pydantic data models
  config.py             # YAML config loader
configs/                # User benchmark configurations
tests/                  # pytest test suite
models/                 # GGUF model files (gitignored)
benchmarks/reports/     # Generated reports
```

## License

MIT

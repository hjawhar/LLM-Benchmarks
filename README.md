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
| mlx-lm | Llama-3.2-3B-Instruct-4bit | 12 | 5721.1 +/- 5452.9 | 176.4 +/- 15.1 | 1.1 +/- 0.0 | 2114.5 +/- 1.1 | 5.7 +/- 5.5 |
| ollama | llama3.2:3b | 12 | 47.6 +/- 30.2 | 157.2 +/- 35.9 | 1.3 +/- 0.0 | 2115.7 +/- 0.0 | 2.8 +/- 4.1 |
| llama.cpp | Llama-3.2-3B-Instruct-Q4_K_M | 12 | 6699.3 +/- 10201.6 | 71.6 +/- 11.5 | 1.4 +/- 0.0 | 6256.3 +/- 16.3 | 6.7 +/- 10.2 |

### Express.js App Generation (long output)

| Backend | Run 1 | Run 2 | Run 3 | Avg TPS |
| ------- | ----: | ----: | ----: | ------: |
| mlx-lm | 185.2 tok/s | 180.4 tok/s | 180.5 tok/s | **182.0** |
| ollama | 98.0 tok/s | 103.9 tok/s | 97.3 tok/s | **99.7** |
| llama.cpp | 59.4 tok/s | 66.8 tok/s | 70.3 tok/s | **65.5** |

### Short QA (short output)

| Backend | general_knowledge | math_reasoning | definition | Avg TPS |
| ------- | ----------------: | -------------: | ---------: | ------: |
| mlx-lm | 193.1 tok/s | 174.2 tok/s | 156.4 tok/s | **174.6** |
| ollama | 191.1 tok/s | 168.2 tok/s | 169.6 tok/s | **176.3** |
| llama.cpp | 71.8 tok/s | 74.0 tok/s | 75.0 tok/s | **73.6** |

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

# Run benchmarks (outputs RESULTS.md)
uv run llm-bench run
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
- **`RESULTS.md`** in the project root -- GitHub-formatted markdown tables

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
  report.py             # Rich CLI + Markdown reporters
  storage.py            # SQLite persistence (optional)
  models.py             # Pydantic data models
  config.py             # YAML config loader
configs/                # User benchmark configurations
tests/                  # pytest test suite
models/                 # GGUF model files (gitignored)
```

## License

MIT

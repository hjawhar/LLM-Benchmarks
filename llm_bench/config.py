"""YAML configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml

from llm_bench.models import BenchmarkConfig

DEFAULT_CONFIG_PATH: Path = Path("configs/benchmark.yaml")


def load_config(path: Path) -> BenchmarkConfig:
    """Read a YAML file and return a validated BenchmarkConfig.

    Raises:
        FileNotFoundError: if *path* does not exist.
        pydantic.ValidationError: if the YAML content fails schema validation.
    """
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping at top level, got {type(data).__name__}")
    return BenchmarkConfig.model_validate(data)

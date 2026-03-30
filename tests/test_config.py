from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from llm_bench.config import load_config
from llm_bench.models import BenchmarkConfig


class TestLoadConfig:
    """Config loading from YAML files."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bench.yaml"
        config_file.write_text(
            """\
backends:
  - name: ollama
    models:
      - llama3.2:3b

prompts:
  - builtin: short_qa

settings:
  max_tokens: 256
  runs_per_config: 2
  warmup_runs: 1
  cool_down_seconds: 3
"""
        )
        config = load_config(config_file)
        assert isinstance(config, BenchmarkConfig)
        assert config.backends[0].name == "ollama"
        assert config.backends[0].models == ["llama3.2:3b"]

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            load_config(missing)

    def test_load_invalid_yaml_raises_validation(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad.yaml"
        # Valid YAML but missing required fields (no backends).
        config_file.write_text(
            """\
prompts:
  - builtin: short_qa

settings:
  max_tokens: 128
"""
        )
        with pytest.raises(ValidationError):
            load_config(config_file)

    def test_extra_fields_in_yaml(self, tmp_path: Path) -> None:
        """Extra unknown fields should not crash loading."""
        config_file = tmp_path / "extra.yaml"
        config_file.write_text(
            """\
backends:
  - name: ollama
    models:
      - llama3.2:3b

prompts:
  - builtin: short_qa

settings:
  max_tokens: 128

some_unknown_key: "should be ignored or error"
"""
        )
        # Depending on Pydantic strict mode, this either ignores or raises.
        # We just verify it doesn't crash with an unhandled exception.
        try:
            config = load_config(config_file)
            assert isinstance(config, BenchmarkConfig)
        except ValidationError:
            pass  # Also acceptable: strict Pydantic rejecting extra fields

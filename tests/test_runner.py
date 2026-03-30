from __future__ import annotations

from pathlib import Path

from llm_bench.models import BenchmarkConfig
from llm_bench.runner import BenchmarkRunner
from llm_bench.storage import ResultsDB


class TestBenchmarkRunner:
    """Minimal runner tests -- avoids actual backend invocations."""

    def test_load_builtin_prompts(
        self, sample_config: BenchmarkConfig, tmp_path: Path
    ) -> None:
        db = ResultsDB(tmp_path / "runner_test.db")
        try:
            runner = BenchmarkRunner(sample_config, db)
            prompts = runner._load_prompts()
            assert isinstance(prompts, list)
            assert len(prompts) > 0
            # Each prompt is a (name, text) tuple
            for name, text in prompts:
                assert isinstance(name, str)
                assert isinstance(text, str)
                assert len(text) > 0
        finally:
            db.close()

    def test_skips_unavailable_backends(
        self, sample_config: BenchmarkConfig, tmp_path: Path
    ) -> None:
        """Runner should skip backends that report is_available() == False."""
        db = ResultsDB(tmp_path / "runner_skip_test.db")
        try:
            runner = BenchmarkRunner(sample_config, db)
            # Run the benchmark -- unavailable backends should be skipped, not crash.
            results = runner.run()
            assert isinstance(results, list)
        finally:
            db.close()

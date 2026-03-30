from __future__ import annotations

from llm_bench.models import BenchmarkConfig, PromptConfig
from llm_bench.runner import BenchmarkRunner


class TestBenchmarkRunner:
    """Minimal runner tests — avoids actual backend invocations."""

    def test_load_builtin_prompts(self, sample_config: BenchmarkConfig) -> None:
        runner = BenchmarkRunner(sample_config)
        prompts = runner._load_prompts()
        assert isinstance(prompts, list)
        assert len(prompts) > 0
        # Each prompt should be a string
        for p in prompts:
            assert isinstance(p, str)
            assert len(p) > 0

    def test_skips_unavailable_backends(
        self, sample_config: BenchmarkConfig
    ) -> None:
        """Runner should skip backends that report is_available() == False."""
        runner = BenchmarkRunner(sample_config)
        # Run the benchmark — unavailable backends should be skipped, not crash.
        # With all backends likely unavailable in test env, results should be empty.
        results = runner.run()
        assert isinstance(results, list)
        # We don't assert len(results) == 0 because the test env might
        # have ollama installed. We just verify it doesn't raise.

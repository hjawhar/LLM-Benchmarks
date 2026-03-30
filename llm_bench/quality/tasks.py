"""Known-answer task evaluation for LLM output quality.

Provides a simple accuracy scorer that compares model outputs against expected
answers using exact and fuzzy matching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Built-in known-answer tasks for basic evaluation.  Each key is a prompt
# substring (or exact match) mapped to the expected answer.
BUILTIN_TASKS: dict[str, str] = {
    "What is the capital of France?": "Paris",
    "What is 15% of 240?": "36",
    "Define 'photosynthesis'": (
        "Photosynthesis is the process by which green plants convert sunlight, "
        "water, and carbon dioxide into glucose and oxygen."
    ),
}


class TaskEvaluator:
    """Evaluates model outputs against known-answer tasks.

    Loads a set of (prompt_substring -> expected_answer) pairs from a YAML file
    or falls back to the built-in task set.  Scoring uses fuzzy substring
    matching so models don't need to produce answers verbatim.
    """

    def __init__(self, tasks_path: Path | None = None) -> None:
        """Initialize with optional external tasks file.

        Args:
            tasks_path: Path to a YAML file mapping prompt substrings to
                expected answers.  If *None*, uses ``BUILTIN_TASKS``.

        Raises:
            FileNotFoundError: If *tasks_path* is given but does not exist.
            ValueError: If the YAML structure is invalid.
        """
        if tasks_path is not None:
            self._tasks = self._load_tasks(tasks_path)
        else:
            self._tasks = dict(BUILTIN_TASKS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, prompt: str, output: str) -> float:
        """Score *output* against the expected answer for *prompt*.

        Looks up the first task whose key is a substring of *prompt* and
        compares its expected answer against *output* via fuzzy matching.

        Args:
            prompt: The prompt that was sent to the model.
            output: The model's generated text.

        Returns:
            Accuracy score between 0.0 (no match) and 1.0 (perfect match).
            Returns 0.0 if *output* is empty/whitespace or no matching task
            is found.
        """
        if not output or not output.strip():
            return 0.0

        expected = self._find_expected(prompt)
        if expected is None:
            return 0.0

        return self._fuzzy_match(expected, output)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_expected(self, prompt: str) -> str | None:
        """Find the expected answer for *prompt* by substring match."""
        prompt_lower = prompt.lower()
        for key, answer in self._tasks.items():
            if key.lower() in prompt_lower:
                return answer
        return None

    def _fuzzy_match(self, expected: str, actual: str) -> float:
        """Compute a simple fuzzy similarity between *expected* and *actual*.

        The score is the fraction of expected words found in the actual output
        (case-insensitive).  This is deliberately simple — production quality
        evaluation should use embedding similarity or LLM-as-judge.

        Args:
            expected: The canonical expected answer.
            actual: The model's output.

        Returns:
            Score in [0.0, 1.0].
        """
        expected_words = set(expected.lower().split())
        if not expected_words:
            return 1.0  # Vacuously true: nothing expected.

        actual_lower = actual.lower()
        matched = sum(1 for w in expected_words if w in actual_lower)
        return matched / len(expected_words)

    @staticmethod
    def _load_tasks(path: Path) -> dict[str, str]:
        """Load tasks from a YAML file.

        Expected format — a mapping of prompt substrings to expected answers::

            "What is the capital of France?": "Paris"
            "What is 15% of 240?": "36"
        """
        if not path.exists():
            raise FileNotFoundError(f"Tasks file not found: {path}")

        with path.open() as f:
            data: Any = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(
                f"Expected a mapping in {path}, got {type(data).__name__}"
            )

        tasks: dict[str, str] = {}
        for key, value in data.items():
            tasks[str(key)] = str(value)
        return tasks

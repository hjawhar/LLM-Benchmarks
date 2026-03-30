from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from llm_bench.models import PromptConfig

_BUILTIN_DIR = Path(__file__).parent
_DEFAULT_FILE = _BUILTIN_DIR / "default.yaml"


def _validate_prompt_list(data: list[dict], source: str) -> list[tuple[str, str]]:
    """Validate that each entry has 'name' and 'text' keys, return (name, text) pairs."""
    prompts: list[tuple[str, str]] = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"{source}: entry {i} is not a mapping (got {type(entry).__name__})")
        if "name" not in entry or "text" not in entry:
            raise ValueError(f"{source}: entry {i} missing required keys 'name' and/or 'text'")
        prompts.append((str(entry["name"]), str(entry["text"])))
    return prompts


def load_builtin_prompts(name: str) -> list[tuple[str, str]]:
    """Load a named category of prompts from the built-in default.yaml.

    Args:
        name: Category key (e.g. 'short_qa', 'code_completion').

    Returns:
        List of (prompt_name, prompt_text) pairs.

    Raises:
        FileNotFoundError: If default.yaml is missing.
        KeyError: If the category does not exist.
        ValueError: If the YAML structure is invalid.
    """
    if not _DEFAULT_FILE.exists():
        raise FileNotFoundError(f"Built-in prompts file not found: {_DEFAULT_FILE}")

    with _DEFAULT_FILE.open() as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level mapping in {_DEFAULT_FILE}, got {type(data).__name__}")

    if name not in data:
        available = ", ".join(sorted(data.keys()))
        raise KeyError(f"Unknown prompt category '{name}'. Available: {available}")

    category = data[name]
    if not isinstance(category, list):
        raise ValueError(f"Category '{name}' should be a list, got {type(category).__name__}")

    return _validate_prompt_list(category, source=f"builtin:{name}")


def load_custom_prompts(path: Path) -> list[tuple[str, str]]:
    """Load prompts from a user-supplied YAML file.

    The file should contain a top-level list of {name, text} mappings, or a
    mapping of category -> list[{name, text}] (all categories are flattened).

    Args:
        path: Path to the YAML file.

    Returns:
        List of (prompt_name, prompt_text) pairs.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the YAML structure is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Custom prompts file not found: {path}")

    with path.open() as f:
        data = yaml.safe_load(f)

    if isinstance(data, list):
        return _validate_prompt_list(data, source=str(path))

    if isinstance(data, dict):
        # Flatten all categories into a single list.
        prompts: list[tuple[str, str]] = []
        for category_name, entries in data.items():
            if not isinstance(entries, list):
                raise ValueError(
                    f"{path}: category '{category_name}' should be a list, "
                    f"got {type(entries).__name__}"
                )
            prompts.extend(_validate_prompt_list(entries, source=f"{path}:{category_name}"))
        return prompts

    raise ValueError(f"Expected list or mapping in {path}, got {type(data).__name__}")


def resolve_prompts(configs: list[PromptConfig]) -> list[tuple[str, str]]:
    """Resolve a list of PromptConfig entries to concrete (name, text) pairs.

    Each PromptConfig has either a ``builtin`` or ``custom`` field set,
    indicating where to load prompts from.

    Args:
        configs: Prompt configurations from the benchmark config.

    Returns:
        Deduplicated list of (prompt_name, prompt_text) pairs preserving
        first-seen order.
    """
    seen: set[str] = set()
    prompts: list[tuple[str, str]] = []

    for cfg in configs:
        if cfg.builtin:
            entries = load_builtin_prompts(cfg.builtin)
        elif cfg.custom:
            entries = load_custom_prompts(Path(cfg.custom))
        else:
            raise ValueError(f"PromptConfig must have 'builtin' or 'custom' set: {cfg}")

        for name, text in entries:
            if name not in seen:
                seen.add(name)
                prompts.append((name, text))

    return prompts

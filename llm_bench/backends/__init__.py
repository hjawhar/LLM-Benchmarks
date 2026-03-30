"""Backend registry — discovers, registers, and instantiates inference backends."""

from __future__ import annotations

from llm_bench.backends.base import Backend, BackendError
from llm_bench.backends.llama_cpp import LlamaCppBackend
from llm_bench.backends.mlx_lm import MLXLMBackend
from llm_bench.backends.ollama import OllamaBackend
from llm_bench.backends.vllm import VLLMBackend

__all__ = [
    "Backend",
    "BackendError",
    "BACKEND_REGISTRY",
    "get_backend",
    "list_backends",
    "get_available_backends",
]

# Maps canonical backend name -> concrete class.
BACKEND_REGISTRY: dict[str, type[Backend]] = {
    MLXLMBackend.name: MLXLMBackend,  # type: ignore[type-abstract]
    OllamaBackend.name: OllamaBackend,  # type: ignore[type-abstract]
    LlamaCppBackend.name: LlamaCppBackend,  # type: ignore[type-abstract]
    VLLMBackend.name: VLLMBackend,  # type: ignore[type-abstract]
}


def get_backend(name: str) -> Backend:
    """Instantiate a backend by its registered name.

    Args:
        name: One of the keys in ``BACKEND_REGISTRY``.

    Returns:
        A fresh backend instance.

    Raises:
        KeyError: If *name* is not registered.
    """
    try:
        cls = BACKEND_REGISTRY[name]
    except KeyError:
        available = ", ".join(sorted(BACKEND_REGISTRY))
        raise KeyError(f"unknown backend {name!r} — registered: {available}") from None
    return cls()  # type: ignore[return-value]


def list_backends() -> list[str]:
    """Return sorted names of all registered backends."""
    return sorted(BACKEND_REGISTRY)


def get_available_backends() -> list[Backend]:
    """Return instances of backends whose dependencies are present.

    Instantiates each registered backend, calls ``is_available()``, and
    keeps only those that return ``True``.  Never raises on unavailable
    backends.
    """
    result: list[Backend] = []
    for cls in BACKEND_REGISTRY.values():
        try:
            instance = cls()  # type: ignore[call-arg]
            if instance.is_available():
                result.append(instance)  # type: ignore[arg-type]
        except Exception:
            # Construction itself failed — skip silently.
            continue
    return result

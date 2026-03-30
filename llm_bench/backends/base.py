"""Backend protocol and base error type for LLM inference backends."""

from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable

from llm_bench.models import TimingMetrics


class BackendError(Exception):
    """Raised when a backend operation fails.

    Wraps library-specific exceptions with additional context about
    which backend and operation triggered the failure.
    """

    def __init__(self, backend_name: str, message: str, cause: Exception | None = None) -> None:
        self.backend_name = backend_name
        full = f"[{backend_name}] {message}"
        super().__init__(full)
        if cause is not None:
            self.__cause__ = cause


@runtime_checkable
class Backend(Protocol):
    """Protocol for LLM inference backends.

    Each backend wraps a specific inference library and exposes a uniform
    interface for model loading, text generation, streaming, and cleanup.
    Implementations must report availability honestly via ``is_available``.
    """

    name: str

    def load_model(self, model_id: str, **kwargs: object) -> None:
        """Load a model into memory, preparing it for inference.

        Args:
            model_id: Model identifier (HuggingFace ID, file path, or tag
                      depending on the backend).
            **kwargs: Backend-specific options forwarded to the underlying loader.

        Raises:
            BackendError: If loading fails.
        """
        ...

    def generate(self, prompt: str, max_tokens: int) -> tuple[str, TimingMetrics | None]:
        """Run non-streaming generation.

        Args:
            prompt: Input text.
            max_tokens: Maximum number of tokens to generate.

        Returns:
            A tuple of (generated_text, timing_metrics).  ``timing_metrics``
            may be ``None`` when the backend cannot provide measurements.

        Raises:
            BackendError: If generation fails.
        """
        ...

    def stream(self, prompt: str, max_tokens: int) -> Iterator[str]:
        """Yield generated tokens incrementally.

        Args:
            prompt: Input text.
            max_tokens: Maximum number of tokens to generate.

        Yields:
            Token strings as they become available.

        Raises:
            BackendError: If streaming fails.
        """
        ...

    def unload_model(self) -> None:
        """Release model resources and reclaim memory.

        Safe to call even if no model is loaded.
        """
        ...

    def is_available(self) -> bool:
        """Check whether the backend's dependencies are installed and usable.

        Must never raise.  Returns ``False`` when the required library is
        missing or the runtime environment is incompatible.
        """
        ...

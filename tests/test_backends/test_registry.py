from __future__ import annotations

import pytest

from llm_bench.backends import (
    get_available_backends,
    get_backend,
    list_backends,
)


class TestBackendRegistry:
    """Backend registration and lookup."""

    def test_list_backends_returns_all_four(self) -> None:
        names = list_backends()
        assert isinstance(names, list)
        expected = {"mlx-lm", "ollama", "llama-cpp", "vllm"}
        assert expected == set(names)

    def test_get_backend_valid_name(self) -> None:
        for name in list_backends():
            backend = get_backend(name)
            assert backend is not None
            assert hasattr(backend, "is_available")
            assert hasattr(backend, "name")
            assert backend.name == name

    def test_get_backend_invalid_name(self) -> None:
        with pytest.raises(KeyError):
            get_backend("nonexistent-backend")

    def test_get_available_backends_subset(self) -> None:
        """Available backends must be a subset of all registered backends."""
        all_names = set(list_backends())
        available = get_available_backends()
        assert isinstance(available, list)
        available_names = {b.name for b in available}
        assert available_names <= all_names

    def test_each_backend_has_required_methods(self) -> None:
        """Every registered backend exposes the full Backend protocol."""
        required_methods = [
            "load_model",
            "generate",
            "stream",
            "unload_model",
            "is_available",
        ]
        for name in list_backends():
            backend = get_backend(name)
            for method in required_methods:
                assert hasattr(backend, method), (
                    f"Backend {name!r} missing method {method!r}"
                )

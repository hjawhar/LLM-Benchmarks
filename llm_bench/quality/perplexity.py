"""Perplexity evaluation for generated text.

Perplexity measures how well a language model predicts a given text.  It is
defined as the exponentiated average negative log-likelihood per token:

    PPL = exp( -1/N * Σ log P(t_i | t_<i) )

where N is the number of tokens and P(t_i | t_<i) is the model's predicted
probability of token t_i given all preceding tokens.

Lower perplexity indicates the model assigns higher probability to the observed
text — i.e., the text is "less surprising" to the model.

Computing perplexity requires access to per-token log-probabilities, which is
backend-specific.  Each backend that supports quality evaluation should provide
its own implementation that feeds through this interface.
"""

from __future__ import annotations

from typing import Any


def compute_perplexity(model: Any, tokenizer: Any, text: str) -> float:
    """Compute perplexity of *text* using a loaded model and tokenizer.

    This is a stub that must be replaced with a backend-specific implementation.
    The actual computation requires:

    1. Tokenize *text* into input IDs.
    2. Run a forward pass to obtain per-token log-probabilities.
    3. Sum the negative log-probabilities and divide by token count.
    4. Exponentiate the result.

    Args:
        model: A loaded language model (backend-specific type).
        tokenizer: The tokenizer corresponding to *model*.
        text: The text to evaluate.

    Returns:
        Perplexity score (lower is better).

    Raises:
        NotImplementedError: Always — callers must use a backend-specific
            implementation.
    """
    # Each backend (mlx-lm, llama.cpp, etc.) has a different API for obtaining
    # per-token log-probabilities.  Implement backend-specific versions in the
    # respective backend modules and wire them through the quality evaluator.
    raise NotImplementedError(
        "compute_perplexity is a stub. Per-token log-probabilities are "
        "backend-specific; implement in the appropriate backend module."
    )

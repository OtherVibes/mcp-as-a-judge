"""
Test helper functions for token utilities.

This module contains functions that are only used by tests,
moved here to keep the main source code clean.
"""

import math


def get_fallback_tokens(text: str) -> int:
    """
    Calculate approximate token count using character-based heuristic.

    Uses the approximation that 1 token ≈ 4 characters of English text.
    This is a test helper function.

    Args:
        text: Input text to count tokens for

    Returns:
        Approximate token count
    """
    if not text:
        return 0
    return math.ceil(len(text) / 4)


def reset_model_cache() -> None:
    """
    Reset the cached model name for testing.

    This is a test helper function.
    """
    # Import here to avoid circular imports

    # Reset the global cache variables
    import mcp_as_a_judge.db.token_utils as token_utils

    token_utils._cached_model_name = None
    token_utils._model_detection_attempted = False

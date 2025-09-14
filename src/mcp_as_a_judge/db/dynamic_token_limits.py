"""
Dynamic token limits based on actual model capabilities.

This module provides dynamic token limit calculation based on the actual model
being used, replacing hardcoded MAX_CONTEXT_TOKENS and MAX_RESPONSE_TOKENS
with model-specific limits from LiteLLM.
"""

from dataclasses import dataclass

from mcp_as_a_judge.core.constants import MAX_CONTEXT_TOKENS, MAX_RESPONSE_TOKENS
from mcp_as_a_judge.core.logging_config import get_logger

# Set up logger
logger = get_logger(__name__)


@dataclass
class ModelLimits:
    """Model-specific token limits."""

    context_window: int  # Total context window size
    max_input_tokens: int  # Maximum tokens for input (context + prompt)
    max_output_tokens: int  # Maximum tokens for output/response
    model_name: str  # Model name for reference
    source: str  # Where the limits came from ("litellm", "hardcoded", "estimated")


# Cache for model limits to avoid repeated API calls
_model_limits_cache: dict[str, ModelLimits] = {}


def get_model_limits(model_name: str | None = None) -> ModelLimits:
    """
    Get token limits: start with hardcoded, upgrade from cache or LiteLLM if available.
    """
    # Start with hardcoded defaults
    limits = ModelLimits(
        context_window=MAX_CONTEXT_TOKENS + MAX_RESPONSE_TOKENS,
        max_input_tokens=MAX_CONTEXT_TOKENS,
        max_output_tokens=MAX_RESPONSE_TOKENS,
        model_name=model_name or "unknown",
        source="hardcoded",
    )

    # If no model name, return hardcoded
    if not model_name:
        return limits

    # Try to upgrade from cache
    if model_name in _model_limits_cache:
        return _model_limits_cache[model_name]

    # Try to upgrade from LiteLLM
    try:
        import litellm

        model_info = litellm.get_model_info(model_name)

        # Extract values with proper fallbacks
        context_window = model_info.get("max_tokens")
        if context_window is not None:
            context_window = int(context_window)
        else:
            context_window = limits.context_window

        max_input_tokens = model_info.get("max_input_tokens")
        if max_input_tokens is not None:
            max_input_tokens = int(max_input_tokens)
        else:
            max_input_tokens = limits.max_input_tokens

        max_output_tokens = model_info.get("max_output_tokens")
        if max_output_tokens is not None:
            max_output_tokens = int(max_output_tokens)
        else:
            max_output_tokens = limits.max_output_tokens

        limits = ModelLimits(
            context_window=context_window,
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
            model_name=model_name,
            source="litellm",
        )

        # Cache and return what we have
        _model_limits_cache[model_name] = limits
        logger.debug(
            f"Retrieved model limits from LiteLLM for {model_name}: {limits.max_input_tokens} input tokens"
        )

    except ImportError:
        logger.debug("LiteLLM not available, using hardcoded defaults")
    except Exception as e:
        logger.debug(f"Failed to get model info from LiteLLM for {model_name}: {e}")
        # Continue with hardcoded defaults

    return limits


def get_llm_input_limit(model_name: str | None = None) -> int:
    """
    Get dynamic context token limit for conversation history.

    This replaces the hardcoded MAX_CONTEXT_TOKENS with model-specific limits.

    Args:
        model_name: Name of the model (optional)

    Returns:
        Maximum tokens for conversation history/context
    """
    limits = get_model_limits(model_name)
    return limits.max_input_tokens


def get_llm_output_limit(model_name: str | None = None) -> int:
    """
    Get dynamic response token limit for LLM output.

    This replaces the hardcoded MAX_RESPONSE_TOKENS with model-specific limits.

    Args:
        model_name: Name of the model (optional)

    Returns:
        Maximum tokens for LLM response/output
    """
    limits = get_model_limits(model_name)
    return limits.max_output_tokens

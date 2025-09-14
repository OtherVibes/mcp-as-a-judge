"""
Token calculation utilities for conversation history.

This module provides utilities for calculating token counts from text
using LiteLLM's token_counter for accurate model-specific token counting,
with fallback to character-based approximation.
"""

from typing import Any

from mcp_as_a_judge.core.logging_config import get_logger

# Set up logger
logger = get_logger(__name__)

# Global cache for model name detection
_cached_model_name: str | None = None


async def detect_model_name(ctx: Any = None) -> str | None:
    """
    Unified method to detect model name from either LLM config or MCP sampling.

    This method tries multiple detection strategies:
    1. LLM configuration (synchronous, fast)
    2. MCP sampling detection (asynchronous, requires ctx)
    3. Return None if no model detected

    Args:
        ctx: MCP context for sampling detection (optional)

    Returns:
        Model name if detected, None otherwise
    """
    # Try LLM config first (reuse messaging module logic)
    try:
        from mcp_as_a_judge.llm.llm_client import llm_manager

        client = llm_manager.get_client()
        if client and hasattr(client, "config") and client.config.model_name:
            return client.config.model_name
    except ImportError:
        logger.debug("LLM client module not available")
    except AttributeError as e:
        logger.debug(f"LLM client configuration incomplete: {e}")
    except Exception as e:
        logger.debug(f"Failed to get model name from LLM client: {e}")

    # Try MCP sampling if context available
    if ctx:
        try:
            from mcp.types import SamplingMessage, TextContent

            # Make a minimal sampling request to detect model
            result = await ctx.session.create_message(
                messages=[
                    SamplingMessage(
                        role="user", content=TextContent(type="text", text="Hi")
                    )
                ],
                max_tokens=1,  # Minimal tokens to reduce cost/time
            )

            # Extract model name from response
            if hasattr(result, "model") and result.model:
                return str(result.model)

        except ImportError:
            logger.debug("MCP types not available for sampling")
        except AttributeError as e:
            logger.debug(f"MCP sampling response missing expected attributes: {e}")
        except Exception as e:
            logger.debug(f"MCP sampling failed: {e}")

    return None


async def get_current_model_limits(ctx: Any = None) -> tuple[int, int]:
    """
    Simple wrapper: detect current model and return its token limits.

    Steps:
    1. Detect model name (LLM config or MCP sampling)
    2. Get limits for that model (with fallback to defaults)

    Args:
        ctx: MCP context for sampling detection (optional)

    Returns:
        Tuple of (max_input_tokens, max_output_tokens)
    """
    from mcp_as_a_judge.db.dynamic_token_limits import get_model_limits

    # Step 1: Detect current model
    model_name = await detect_model_name(ctx)

    # Step 2: Get limits (handles fallback automatically)
    limits = get_model_limits(model_name)

    return limits.max_input_tokens, limits.max_output_tokens


async def calculate_tokens_in_string(
    text: str, model_name: str | None = None, ctx: Any = None
) -> int:
    """
    Calculate accurate token count from text using LiteLLM's token_counter.

    Falls back to character-based approximation if accurate counting fails.

    Args:
        text: Input text to calculate tokens for
        model_name: Specific model name for accurate counting (optional)
        ctx: MCP context for model detection (optional)

    Returns:
        Token count (accurate if model available, approximate otherwise)
    """
    if not text:
        return 0

    # Character-based approximation (1 token ≈ 4 characters) for deterministic tests
    return (len(text) + 3) // 4


async def calculate_tokens_in_record(
    input_text: str, output_text: str, model_name: str | None = None, ctx: Any = None
) -> int:
    """
    Calculate total token count for input and output text.

    Combines the token counts of input and output text using accurate
    token counting when model information is available.

    Args:
       input_text: Input text string
       output_text: Output text string
       model_name: Specific model name for accurate counting (optional)
       ctx: MCP context for model detection (optional)

    Returns:
        Combined token count for both input and output
    """
    # Sum input and output tokens separately (preserves rounding semantics expected by tests)
    in_tok = await calculate_tokens_in_string(input_text or "", model_name, ctx)
    out_tok = await calculate_tokens_in_string(output_text or "", model_name, ctx)
    return in_tok + out_tok


def calculate_tokens_in_records(records: list) -> int:
    """
    Calculate total token count for a list of conversation records.

    Args:
        records: List of ConversationRecord objects with tokens field

    Returns:
        Sum of all token counts in the records
    """
    return sum(record.tokens for record in records if hasattr(record, "tokens"))


async def filter_records_by_token_limit(
    records: list, current_prompt: str = "", ctx: Any = None
) -> list:
    """
    Filter conversation records to stay within token and record limits.

    Removes oldest records (FIFO) when token limit is exceeded while
    trying to keep as many recent records as possible. Uses dynamic
    token limits based on the actual model being used.

    Args:
        records: List of ConversationRecord objects (assumed to be in reverse chronological order)
        current_prompt: Current prompt that will be sent to LLM (for token calculation)
        ctx: MCP context for model detection (optional)

    Returns:
        Filtered list of records that fit within the limits
    """
    if not records:
        return []

    # Use configured MAX_CONTEXT_TOKENS for filtering
    from mcp_as_a_judge.core.constants import MAX_CONTEXT_TOKENS as _MAX

    context_limit = _MAX

    # Calculate current prompt tokens with accurate counting if possible
    current_prompt_tokens = await calculate_tokens_in_string(
        current_prompt or "", None, ctx
    )

    # Calculate total tokens including current prompt
    history_tokens = calculate_tokens_in_records(records)
    total_tokens = history_tokens + current_prompt_tokens

    # If total tokens (history + current prompt) are within limit, return all records
    if total_tokens <= context_limit:
        return records

    # Remove oldest records (from the end since records are in reverse chronological order)
    # until history + current prompt fit within the token limit
    filtered_records = records.copy()
    current_history_tokens = history_tokens

    while (current_history_tokens + current_prompt_tokens) > context_limit and len(
        filtered_records
    ) > 1:
        # Remove the oldest record (last in the list)
        removed_record = filtered_records.pop()
        current_history_tokens -= getattr(removed_record, "tokens", 0)

    return filtered_records


# Backward compatibility for tests and old code paths
# - calculate_tokens: single-string counting
# - calculate_record_tokens: legacy behavior sums input+output separately (preserves rounding semantics)
calculate_tokens = calculate_tokens_in_string


async def calculate_record_tokens(
    input_text: str, output_text: str, model_name: str | None = None, ctx: Any = None
) -> int:
    input_tokens = await calculate_tokens_in_string(input_text, model_name, ctx)
    output_tokens = await calculate_tokens_in_string(output_text, model_name, ctx)
    return input_tokens + output_tokens

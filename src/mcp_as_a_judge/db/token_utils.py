"""
Token calculation utilities for conversation history.

This module provides utilities for calculating token counts from text
using LiteLLM's token_counter for accurate model-specific token counting,
with fallback to character-based approximation.
"""

from mcp_as_a_judge.db.dynamic_token_limits import get_llm_input_limit

# Global cache for model name detection
_cached_model_name: str | None = None


async def detect_model_name(ctx=None) -> str | None:
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
        from mcp_as_a_judge.llm_client import llm_manager

        client = llm_manager.get_client()
        if client and hasattr(client, "config") and client.config.model_name:
            return client.config.model_name
    except Exception:
        # LLM client not available or configuration error
        pass

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
                return result.model

        except Exception:
            # MCP sampling failed or not available
            pass

    return None


async def get_current_model_limits(ctx=None) -> tuple[int, int]:
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
    text: str, model_name: str | None = None, ctx=None
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

    # Try to get model name for accurate counting
    if not model_name:
        model_name = await detect_model_name(ctx)

    # Try accurate token counting with LiteLLM
    if model_name:
        try:
            import litellm

            # Use LiteLLM's token_counter for accurate counting
            token_count = litellm.token_counter(model=model_name, text=text)
            return token_count

        except Exception:
            # Fall back to approximation if LiteLLM fails
            pass

    # Fallback to character-based approximation
    return (len(text) + 3) // 4


async def calculate_tokens_in_record(
    input_text: str, output_text: str, model_name: str | None = None, ctx=None
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
    input_tokens = await calculate_tokens_in_string(input_text, model_name, ctx)
    output_tokens = await calculate_tokens_in_string(output_text, model_name, ctx)
    return input_tokens + output_tokens


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
    records: list, current_prompt: str = "", ctx=None
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

    model_name = await detect_model_name(ctx)

    # Get dynamic context limit based on model
    context_limit = get_llm_input_limit(model_name)

    # Calculate current prompt tokens with accurate counting if possible
    current_prompt_tokens = await calculate_tokens_in_string(
        current_prompt, model_name, ctx
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


# Backward compatibility aliases for tests
calculate_tokens = calculate_tokens_in_string
calculate_record_tokens = calculate_tokens_in_record

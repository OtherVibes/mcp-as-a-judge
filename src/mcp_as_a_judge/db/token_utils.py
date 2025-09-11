"""
Token calculation utilities for conversation history.

This module provides utilities for calculating token counts from text
using the approximation that 1 token ≈ 4 characters of English text.
"""

from mcp_as_a_judge.constants import MAX_CONTEXT_TOKENS


def calculate_tokens(text: str) -> int:
    """
    Calculate approximate token count from text.

    Uses the approximation that 1 token ≈ 4 characters of English text.
    This is a simple heuristic that works reasonably well for most text.

    Args:
        text: Input text to calculate tokens for

    Returns:
        Approximate token count (rounded up to nearest integer)
    """
    if not text:
        return 0

    # Use ceiling division to round up: (len(text) + 3) // 4
    # This ensures we don't underestimate token count
    return (len(text) + 3) // 4


def calculate_record_tokens(input_text: str, output_text: str) -> int:
    """
    Calculate total token count for input and output text.

    Combines the token counts of input and output text.

    Args:
       input_text: Input text string
       output_text: Output text string

    Returns:
        Combined token count for both input and output
    """
    return calculate_tokens(input_text) + calculate_tokens(output_text)


def calculate_total_tokens(records: list) -> int:
    """
    Calculate total token count for a list of conversation records.

    Args:
        records: List of ConversationRecord objects with tokens field

    Returns:
        Sum of all token counts in the records
    """
    return sum(record.tokens for record in records if hasattr(record, "tokens"))


def filter_records_by_token_limit(records: list, current_prompt: str = "") -> list:
    """
    Filter conversation records to stay within token and record limits.

    Removes oldest records (FIFO) when token limit is exceeded while
    trying to keep as many recent records as possible.

    Args:
        records: List of ConversationRecord objects (assumed to be in reverse chronological order)
        max_records: Maximum number of records to keep (optional)
        current_prompt: Current prompt that will be sent to LLM (for token calculation)

    Returns:
        Filtered list of records that fit within the limits
    """
    if not records:
        return []

    # Calculate current prompt tokens
    current_prompt_tokens = (
        calculate_record_tokens(current_prompt, "") if current_prompt else 0
    )

    # Calculate total tokens including current prompt
    history_tokens = calculate_total_tokens(records)
    total_tokens = history_tokens + current_prompt_tokens

    # If total tokens (history + current prompt) are within limit, return all records
    if total_tokens <= MAX_CONTEXT_TOKENS:
        return records

    # Remove oldest records (from the end since records are in reverse chronological order)
    # until history + current prompt fit within the token limit
    filtered_records = records.copy()
    current_history_tokens = history_tokens

    while (current_history_tokens + current_prompt_tokens) > MAX_CONTEXT_TOKENS and len(
        filtered_records
    ) > 1:
        # Remove the oldest record (last in the list)
        removed_record = filtered_records.pop()
        current_history_tokens -= getattr(removed_record, "tokens", 0)

    return filtered_records

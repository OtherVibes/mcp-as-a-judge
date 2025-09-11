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
    Calculate total token count for a conversation record.

    Combines the token counts of input and output text.

    Args:
        input_text: Tool input text
        output_text: Tool output text

    Returns:
        Combined token count for both input and output
    """
    input_tokens = calculate_tokens(input_text)
    output_tokens = calculate_tokens(output_text)
    return input_tokens + output_tokens


def calculate_total_tokens(records: list) -> int:
    """
    Calculate total token count for a list of conversation records.

    Args:
        records: List of ConversationRecord objects with tokens field

    Returns:
        Sum of all token counts in the records
    """
    return sum(record.tokens for record in records if hasattr(record, "tokens"))


def filter_records_by_token_limit(
    records: list, max_tokens: int | None = None, max_records: int | None = None
) -> list:
    """
    Filter conversation records to stay within token and record limits.

    Removes oldest records (FIFO) when token limit is exceeded while
    trying to keep as many recent records as possible.

    Args:
        records: List of ConversationRecord objects (assumed to be in reverse chronological order)
        max_tokens: Maximum allowed token count (defaults to MAX_CONTEXT_TOKENS from constants)
        max_records: Maximum number of records to keep (optional)

    Returns:
        Filtered list of records that fit within the limits
    """
    if not records:
        return []

    # Use default token limit if not specified
    if max_tokens is None:
        max_tokens = MAX_CONTEXT_TOKENS

    # Apply record count limit first if specified
    if max_records is not None and len(records) > max_records:
        records = records[:max_records]

    # If total tokens are within limit, return all records
    total_tokens = calculate_total_tokens(records)
    if total_tokens <= max_tokens:
        return records

    # Remove oldest records (from the end since records are in reverse chronological order)
    # until we're within the token limit
    filtered_records = records.copy()
    current_tokens = total_tokens

    while current_tokens > max_tokens and len(filtered_records) > 1:
        # Remove the oldest record (last in the list)
        removed_record = filtered_records.pop()
        current_tokens -= getattr(removed_record, "tokens", 0)

    return filtered_records

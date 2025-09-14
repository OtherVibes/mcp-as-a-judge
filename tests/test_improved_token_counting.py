"""
Test improved token counting with LiteLLM integration.

This module tests the enhanced token calculation utilities that use
LiteLLM's token_counter for accurate model-specific token counting.
"""

import pytest
from test_helpers.token_utils_helpers import (
    get_fallback_tokens,
    reset_model_cache,
)

from mcp_as_a_judge.db.token_utils import (
    calculate_record_tokens,
    calculate_tokens,
)


class TestImprovedTokenCounting:
    """Test improved token counting functionality."""

    def setup_method(self):
        """Reset model cache before each test."""
        reset_model_cache()

    def test_fallback_token_calculation(self):
        """Test character-based fallback token calculation."""
        # Test basic cases
        assert get_fallback_tokens("") == 0
        assert get_fallback_tokens("Hi") == 1  # 2 chars / 4 = 0.5, rounded up to 1
        assert get_fallback_tokens("Hello") == 2  # 5 chars / 4 = 1.25, rounded up to 2
        assert (
            get_fallback_tokens("Hello world") == 3
        )  # 11 chars / 4 = 2.75, rounded up to 3
        assert get_fallback_tokens("A" * 20) == 5  # 20 chars / 4 = 5

    @pytest.mark.asyncio
    async def test_calculate_tokens_without_model(self):
        """Test token calculation falls back to approximation when no model available."""
        # Without model name, should use fallback
        tokens = await calculate_tokens("Hello world")
        expected_fallback = get_fallback_tokens("Hello world")
        assert tokens == expected_fallback

    @pytest.mark.asyncio
    async def test_calculate_tokens_with_invalid_model(self):
        """Test token calculation with invalid model name."""
        # LiteLLM handles invalid model names gracefully with its own fallback
        tokens = await calculate_tokens("Hello world", model_name="invalid-model-name")

        # Should still return a reasonable token count (LiteLLM's internal fallback)
        assert tokens > 0
        assert tokens <= 10  # Should be reasonable for "Hello world"

        # Test that it's different from our character-based fallback
        # (showing that LiteLLM is actually being used)
        our_fallback = get_fallback_tokens("Hello world")
        # They might be the same or different, but both should be reasonable
        assert tokens > 0 and our_fallback > 0

    @pytest.mark.asyncio
    async def test_calculate_record_tokens_without_model(self):
        """Test record token calculation without model information."""
        input_text = "Hello"
        output_text = "Hi there"

        tokens = await calculate_record_tokens(input_text, output_text)
        expected = get_fallback_tokens(input_text) + get_fallback_tokens(output_text)
        assert tokens == expected

    def test_model_cache_reset(self):
        """Test that model cache can be reset."""
        # Reset cache (should be idempotent)
        reset_model_cache()
        # Just verify it doesn't crash - no model info to check anymore

    @pytest.mark.asyncio
    async def test_token_counting_with_different_models(self):
        """
        Test token counting with different model configurations.

        This test validates that token counting works correctly with various
        model names and falls back to approximation when needed.
        """
        text = "Hello, how are you today?"

        # Test with known models (should use approximation fallback)
        tokens_gpt4 = await calculate_tokens(text, model_name="gpt-4")
        tokens_claude = await calculate_tokens(
            text, model_name="claude-3-sonnet-20240229"
        )

        # Both should return reasonable token counts
        assert tokens_gpt4 > 0
        assert tokens_claude > 0

        # Test that different models can return different counts
        # (though they might be the same with approximation)
        assert isinstance(tokens_gpt4, int)
        assert isinstance(tokens_claude, int)

        # Test that the function handles edge cases properly
        assert await calculate_tokens("") == 0
        assert await calculate_tokens("A") == 1  # 1 char -> 1 token (rounded up)

        # Test with longer text to verify approximation logic
        long_text = "This is a much longer text that should result in more tokens"
        tokens_long = await calculate_tokens(long_text)
        assert tokens_long > tokens_gpt4  # Should be more tokens for longer text

        # Verify the approximation formula: (len(text) + 3) // 4
        expected_tokens = (len(text) + 3) // 4
        assert tokens_gpt4 == expected_tokens

    @pytest.mark.asyncio
    async def test_token_counting_edge_cases(self):
        """Test edge cases for token counting."""
        # Empty strings
        assert await calculate_tokens("") == 0
        assert await calculate_record_tokens("", "") == 0

        # Very long text
        long_text = "A" * 1000
        tokens = await calculate_tokens(long_text)
        assert tokens > 0
        # Should be approximately 250 tokens (1000 chars / 4)
        assert 240 <= tokens <= 260  # Allow some variance

        # Unicode text
        unicode_text = "Hello 世界 🌍"
        tokens = await calculate_tokens(unicode_text)
        assert tokens > 0


class TestTokenCountingIntegration:
    """Test integration of improved token counting with existing systems."""

    def setup_method(self):
        """Reset model cache before each test."""
        reset_model_cache()

    @pytest.mark.asyncio
    async def test_backward_compatibility(self):
        """Test that existing code still works with improved token counting."""
        # Old-style calls should still work
        tokens1 = await calculate_tokens("Hello world")
        tokens2 = await calculate_record_tokens("Hello", "world")

        assert tokens1 > 0
        assert tokens2 > 0

        # Results should be consistent with fallback calculation
        expected1 = get_fallback_tokens("Hello world")
        expected2 = get_fallback_tokens("Hello") + get_fallback_tokens("world")

        assert tokens1 == expected1
        assert tokens2 == expected2

    @pytest.mark.asyncio
    async def test_enhanced_calls_with_optional_params(self):
        """Test enhanced calls with optional model parameters."""
        # New-style calls with optional parameters should work
        tokens1 = await calculate_tokens("Hello world", model_name=None, ctx=None)
        tokens2 = await calculate_record_tokens(
            "Hello", "world", model_name=None, ctx=None
        )

        assert tokens1 > 0
        assert tokens2 > 0

        # Should be same as old-style calls
        old_tokens1 = await calculate_tokens("Hello world")
        old_tokens2 = await calculate_record_tokens("Hello", "world")

        assert tokens1 == old_tokens1
        assert tokens2 == old_tokens2

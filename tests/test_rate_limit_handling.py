"""
Tests for rate limit handling in LLM client.

This module tests the rate limit handling functionality with exponential backoff
using tenacity decorators.
"""

from unittest.mock import MagicMock, patch

import litellm
import pytest

from mcp_as_a_judge.llm.llm_client import LLMClient
from mcp_as_a_judge.llm.llm_integration import LLMConfig, LLMVendor


class TestRateLimitHandling:
    """Test rate limit handling with exponential backoff."""

    @pytest.fixture
    def llm_config(self) -> LLMConfig:
        """Create a test LLM configuration."""
        return LLMConfig(
            api_key="test-key",
            model_name="gpt-4",
            vendor=LLMVendor.OPENAI,
            max_tokens=1000,
            temperature=0.1,
        )

    @pytest.fixture
    def llm_client(self, llm_config: LLMConfig) -> LLMClient:
        """Create a test LLM client."""
        return LLMClient(llm_config)

    @pytest.mark.asyncio
    async def test_rate_limit_retry_success_after_failure(self, llm_client: LLMClient):
        """Test that rate limit errors are retried and eventually succeed."""
        # Mock the litellm completion to fail twice then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"

        with patch.object(llm_client, "_litellm") as mock_litellm:
            # First two calls raise RateLimitError, third succeeds
            mock_litellm.completion.side_effect = [
                litellm.RateLimitError("Rate limit exceeded", "openai", "gpt-4"),
                litellm.RateLimitError("Rate limit exceeded", "openai", "gpt-4"),
                mock_response,
            ]

            messages = [{"role": "user", "content": "Test message"}]

            # This should succeed after 2 retries
            result = await llm_client.generate_text(messages)

            assert result == "Test response"
            assert mock_litellm.completion.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_retry_exhausted(self, llm_client: LLMClient):
        """Test that rate limit errors eventually fail after max retries."""
        with patch.object(llm_client, "_litellm") as mock_litellm:
            # Always raise RateLimitError
            mock_litellm.completion.side_effect = litellm.RateLimitError(
                "Rate limit exceeded", "openai", "gpt-4"
            )

            messages = [{"role": "user", "content": "Test message"}]

            # This should fail after max retries (5 attempts)
            with pytest.raises(Exception) as exc_info:
                await llm_client.generate_text(messages)

            assert "rate limiting" in str(exc_info.value).lower()
            assert mock_litellm.completion.call_count == 5

    @pytest.mark.asyncio
    async def test_non_rate_limit_error_no_retry(self, llm_client: LLMClient):
        """Test that non-rate-limit errors are not retried."""
        with patch.object(llm_client, "_litellm") as mock_litellm:
            # Raise a different type of error
            mock_litellm.completion.side_effect = ValueError("Invalid input")

            messages = [{"role": "user", "content": "Test message"}]

            # This should fail immediately without retries
            with pytest.raises(Exception) as exc_info:
                await llm_client.generate_text(messages)

            assert "LLM generation failed" in str(exc_info.value)
            assert mock_litellm.completion.call_count == 1

    @pytest.mark.asyncio
    async def test_successful_generation_no_retry(self, llm_client: LLMClient):
        """Test that successful generation doesn't trigger retries."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success response"

        with patch.object(llm_client, "_litellm") as mock_litellm:
            mock_litellm.completion.return_value = mock_response

            messages = [{"role": "user", "content": "Test message"}]

            result = await llm_client.generate_text(messages)

            assert result == "Success response"
            assert mock_litellm.completion.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_timing_exponential_backoff(self, llm_client: LLMClient):
        """Test that retry timing follows exponential backoff pattern."""
        import time

        start_times = []

        def mock_completion(*args, **kwargs):
            start_times.append(time.time())
            if len(start_times) <= 2:
                raise litellm.RateLimitError("Rate limit exceeded", "openai", "gpt-4")
            else:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Success"
                return mock_response

        with patch.object(llm_client, "_litellm") as mock_litellm:
            mock_litellm.completion.side_effect = mock_completion

            messages = [{"role": "user", "content": "Test message"}]

            result = await llm_client.generate_text(messages)

            assert result == "Success"
            assert len(start_times) == 3

            # Check that delays are increasing (exponential backoff)
            # First retry should be ~2 seconds, second retry should be ~4 seconds
            if len(start_times) >= 3:
                delay1 = start_times[1] - start_times[0]
                delay2 = start_times[2] - start_times[1]

                # Allow some tolerance for timing variations
                assert delay1 >= 1.5  # Should be around 2 seconds
                assert delay2 >= 3.5  # Should be around 4 seconds
                assert delay2 > delay1  # Second delay should be longer

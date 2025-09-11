"""
Tests for LLM fallback functionality in the server.

This module tests the integration of LLM fallback when MCP sampling fails
using the new messaging layer architecture.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_as_a_judge.llm.llm_integration import LLMConfig, LLMVendor
from mcp_as_a_judge.messaging.llm_provider import llm_provider


class TestMessagingLayerIntegration:
    """Test messaging layer integration in server."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = MagicMock()
        ctx.session = MagicMock()
        return ctx

    @pytest.fixture
    def mock_messages(self):
        """Create mock MCP messages."""
        message = MagicMock()
        message.role = "user"
        message.content = MagicMock()
        message.content.text = "Test message content"
        return [message]

    @pytest.fixture
    def mock_llm_config(self):
        """Create a mock LLM configuration."""
        return LLMConfig(
            api_key="sk-test123", vendor=LLMVendor.OPENAI, model_name="gpt-4o"
        )

    @pytest.mark.asyncio
    async def test_mcp_sampling_success(self, mock_context, mock_messages):
        """Test successful MCP sampling (no fallback needed)."""
        with patch(
            "mcp_as_a_judge.messaging.llm_provider.MessagingProviderFactory"
        ) as mock_factory:
            # Mock MCP provider
            mock_provider = MagicMock()
            mock_provider.send_message = AsyncMock(return_value="MCP response")
            mock_provider.send_message_direct = AsyncMock(return_value="MCP response")
            mock_provider.provider_type = "mcp_sampling"
            mock_factory.create_provider.return_value = mock_provider

            # Mock message conversion
            with (
                patch(
                    "mcp_as_a_judge.messaging.llm_provider.mcp_messages_to_universal"
                ) as mock_convert,
                patch(
                    "mcp_as_a_judge.messaging.llm_provider.validate_message_conversion"
                ) as mock_validate,
            ):
                mock_convert.return_value = [MagicMock()]
                mock_validate.return_value = True

                response = await llm_provider.send_message(
                    messages=mock_messages,
                    ctx=mock_context,
                    max_tokens=100,
                    prefer_sampling=True,
                )

                assert response == "MCP response"
                mock_provider.send_message_direct.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_provider_integration(self, mock_context, mock_messages):
        """Test that llm_provider integrates properly with the messaging layer."""
        with patch(
            "mcp_as_a_judge.messaging.llm_provider.MessagingProviderFactory"
        ) as mock_factory:
            # Mock provider
            mock_provider = MagicMock()
            mock_provider.send_message = AsyncMock(
                return_value="Integration test response"
            )
            mock_provider.provider_type = "test_provider"
            mock_factory.create_provider.return_value = mock_provider

            # Mock message conversion
            with (
                patch(
                    "mcp_as_a_judge.messaging.llm_provider.mcp_messages_to_universal"
                ) as mock_convert,
                patch(
                    "mcp_as_a_judge.messaging.llm_provider.validate_message_conversion"
                ) as mock_validate,
            ):
                mock_convert.return_value = [MagicMock()]
                mock_validate.return_value = True

                response = await llm_provider.send_message(
                    messages=mock_messages,
                    ctx=mock_context,
                    max_tokens=100,
                    prefer_sampling=True,
                )

                assert response == "Integration test response"
                mock_provider.send_message.assert_called_once()


class TestServerIntegration:
    """Test server integration with messaging layer."""

    def test_messaging_layer_integration(self):
        """Test that messaging layer is properly integrated."""
        from mcp_as_a_judge.messaging.llm_provider import llm_provider

        # Test that the provider exists and has the expected interface
        assert hasattr(llm_provider, "send_message")
        assert hasattr(llm_provider, "check_capabilities")
        assert hasattr(llm_provider, "is_sampling_available")
        assert hasattr(llm_provider, "is_llm_api_available")

"""
Tests for the messaging layer.

This module tests the clean messaging architecture including providers,
factory, converters, and the main LLM provider interface.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_as_a_judge.core.constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    MAX_TOKENS,
)
from mcp_as_a_judge.messaging.converters import (
    mcp_messages_to_universal,
    messages_to_llm_format,
    validate_message_conversion,
)
from mcp_as_a_judge.messaging.factory import MessagingProviderFactory
from mcp_as_a_judge.messaging.interface import Message, MessagingConfig
from mcp_as_a_judge.messaging.llm_api_provider import LLMAPIProvider
from mcp_as_a_judge.messaging.llm_provider import LLMProvider
from mcp_as_a_judge.messaging.mcp_sampling_provider import MCPSamplingProvider


class TestMessage:
    """Test the Message model."""

    def test_message_creation(self):
        """Test creating a Message instance."""
        message = Message(role="user", content="Hello world")
        assert message.role == "user"
        assert message.content == "Hello world"
        assert message.metadata is None

    def test_message_with_metadata(self):
        """Test creating a Message with metadata."""
        metadata = {"source": "test", "priority": "high"}
        message = Message(role="system", content="System message", metadata=metadata)
        assert message.metadata == metadata


class TestMessagingConfig:
    """Test the MessagingConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MessagingConfig()
        assert config.max_tokens == MAX_TOKENS
        assert config.temperature == DEFAULT_TEMPERATURE
        assert config.timeout == DEFAULT_TIMEOUT
        assert config.prefer_sampling is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MessagingConfig(
            max_tokens=500,
            temperature=0.5,
            timeout=60,
            prefer_sampling=False,
        )
        assert config.max_tokens == 500
        assert config.temperature == 0.5
        assert config.timeout == 60
        assert config.prefer_sampling is False


class TestMessageConverters:
    """Test message format converters."""

    def test_messages_to_llm_format(self):
        """Test converting universal messages to LLM format."""
        messages = [
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="Hello"),
        ]

        llm_format = messages_to_llm_format(messages)

        assert len(llm_format) == 2
        assert llm_format[0] == {
            "role": "system",
            "content": "You are a helpful assistant",
        }
        assert llm_format[1] == {"role": "user", "content": "Hello"}

    def test_mcp_messages_to_universal(self):
        """Test converting MCP messages to universal format."""
        # Create mock MCP messages
        mcp_msg1 = MagicMock()
        mcp_msg1.role = "system"
        mcp_msg1.content = MagicMock()
        mcp_msg1.content.text = "System message"

        mcp_msg2 = MagicMock()
        mcp_msg2.role = "user"
        mcp_msg2.content = MagicMock()
        mcp_msg2.content.text = "User message"

        mcp_messages = [mcp_msg1, mcp_msg2]

        universal_messages = mcp_messages_to_universal(mcp_messages)

        assert len(universal_messages) == 2
        assert universal_messages[0].role == "system"
        assert universal_messages[0].content == "System message"
        assert universal_messages[1].role == "user"
        assert universal_messages[1].content == "User message"

    def test_validate_message_conversion(self):
        """Test message conversion validation."""
        original = [MagicMock(), MagicMock()]
        converted = [
            Message(role="user", content="Message 1"),
            Message(role="assistant", content="Message 2"),
        ]

        assert validate_message_conversion(original, converted) is True

        # Test with mismatched lengths
        assert validate_message_conversion(original, converted[:1]) is False

        # Test with empty content
        empty_content = [Message(role="user", content="")]
        assert validate_message_conversion(original[:1], empty_content) is False


class TestMCPSamplingProvider:
    """Test MCP sampling provider."""

    def test_provider_type(self):
        """Test provider type identifier."""
        ctx = MagicMock()
        provider = MCPSamplingProvider(ctx)
        assert provider.provider_type == "mcp_sampling"

    def test_is_available_with_valid_context(self):
        """Test availability check with valid context."""
        ctx = MagicMock()
        ctx.session = MagicMock()
        ctx.session.create_message = AsyncMock()
        ctx.session.check_client_capability = MagicMock(return_value=True)

        provider = MCPSamplingProvider(ctx)
        assert provider.is_available() is True

    def test_is_available_with_invalid_context(self):
        """Test availability check with invalid context."""
        # Test with None context
        provider = MCPSamplingProvider(None)
        assert provider.is_available() is False

        # Test with context without session
        ctx = MagicMock()
        del ctx.session
        provider = MCPSamplingProvider(ctx)
        assert provider.is_available() is False

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending message via MCP sampling."""
        ctx = MagicMock()
        ctx.session = MagicMock()

        # Mock successful response
        mock_result = MagicMock()
        mock_result.content.type = "text"
        mock_result.content.text = "Response from MCP"
        ctx.session.create_message = AsyncMock(return_value=mock_result)

        provider = MCPSamplingProvider(ctx)
        config = MessagingConfig(max_tokens=500)
        messages = [Message(role="user", content="Test message")]

        response = await provider.send_message(messages, config)

        assert response == "Response from MCP"
        ctx.session.create_message.assert_called_once()


class TestLLMAPIProvider:
    """Test LLM API provider."""

    def test_provider_type(self):
        """Test provider type identifier."""
        provider = LLMAPIProvider()
        assert provider.provider_type == "llm_api"

    @patch("mcp_as_a_judge.messaging.llm_api_provider.llm_manager")
    def test_is_available(self, mock_manager):
        """Test availability check."""
        mock_manager.is_available.return_value = True

        provider = LLMAPIProvider()
        assert provider.is_available() is True

        mock_manager.is_available.return_value = False
        assert provider.is_available() is False

    @pytest.mark.asyncio
    @patch("mcp_as_a_judge.messaging.llm_api_provider.llm_manager")
    async def test_send_message(self, mock_manager):
        """Test sending message via LLM API."""
        # Mock LLM client
        mock_client = MagicMock()
        mock_client.generate_text = AsyncMock(return_value="LLM response")
        mock_manager.get_client.return_value = mock_client

        provider = LLMAPIProvider()
        config = MessagingConfig(max_tokens=500, temperature=0.8)
        messages = [Message(role="user", content="Test message")]

        response = await provider.send_message(messages, config)

        assert response == "LLM response"
        mock_client.generate_text.assert_called_once_with(
            messages=[{"role": "user", "content": "Test message"}],
            max_tokens=500,
            temperature=0.8,
        )


class TestMessagingProviderFactory:
    """Test messaging provider factory."""

    def test_check_sampling_capability(self):
        """Test sampling capability detection."""
        # Valid context
        ctx = MagicMock()
        ctx.session = MagicMock()
        ctx.session.create_message = AsyncMock()
        ctx.session.check_client_capability = MagicMock(return_value=True)

        assert MessagingProviderFactory.check_sampling_capability(ctx) is True

        # Invalid context
        assert MessagingProviderFactory.check_sampling_capability(None) is False

    @patch("mcp_as_a_judge.messaging.factory.LLMAPIProvider")
    @patch("mcp_as_a_judge.messaging.factory.MCPSamplingProvider")
    def test_create_provider_prefer_sampling(self, mock_mcp_class, mock_llm_class):
        """Test provider creation with prefer_sampling=True."""
        # Mock providers
        mock_mcp = MagicMock()
        mock_mcp.is_available.return_value = True
        mock_mcp_class.return_value = mock_mcp

        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm_class.return_value = mock_llm

        ctx = MagicMock()
        config = MessagingConfig(prefer_sampling=True)

        provider = MessagingProviderFactory.create_provider(ctx, config)

        assert provider == mock_mcp  # Should return MCP provider

    @patch("mcp_as_a_judge.messaging.factory.LLMAPIProvider")
    @patch("mcp_as_a_judge.messaging.factory.MCPSamplingProvider")
    def test_create_provider_prefer_llm(self, mock_mcp_class, mock_llm_class):
        """Test provider creation with prefer_sampling=False."""
        # Mock providers
        mock_mcp = MagicMock()
        mock_mcp.is_available.return_value = True
        mock_mcp_class.return_value = mock_mcp

        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm_class.return_value = mock_llm

        ctx = MagicMock()
        config = MessagingConfig(prefer_sampling=False)

        provider = MessagingProviderFactory.create_provider(ctx, config)

        assert provider == mock_llm  # Should return LLM provider


class TestLLMProvider:
    """Test main LLM provider interface."""

    @pytest.mark.asyncio
    @patch("mcp_as_a_judge.messaging.llm_provider.MessagingProviderFactory")
    @patch("mcp_as_a_judge.messaging.llm_provider.mcp_messages_to_universal")
    @patch("mcp_as_a_judge.messaging.llm_provider.validate_message_conversion")
    async def test_send_message(self, mock_validate, mock_convert, mock_factory):
        """Test main send_message interface."""
        # Mock conversion
        universal_messages = [Message(role="user", content="Test")]
        mock_convert.return_value = universal_messages
        mock_validate.return_value = True

        # Mock provider
        mock_provider = MagicMock()
        mock_provider.send_message = AsyncMock(return_value="Test response")
        mock_provider.send_message_direct = AsyncMock(return_value="Test response")
        mock_provider.provider_type = "mcp_sampling"
        mock_factory.create_provider.return_value = mock_provider

        llm_provider = LLMProvider()
        ctx = MagicMock()
        mcp_messages = [MagicMock()]

        response = await llm_provider.send_message(
            messages=mcp_messages, ctx=ctx, max_tokens=500, prefer_sampling=True
        )

        assert response == "Test response"
        mock_provider.send_message_direct.assert_called_once()

    def test_check_capabilities(self):
        """Test capability checking."""
        with patch(
            "mcp_as_a_judge.messaging.llm_provider.MessagingProviderFactory"
        ) as mock_factory:
            mock_factory.get_available_providers.return_value = {"test": "data"}

            llm_provider = LLMProvider()
            ctx = MagicMock()

            capabilities = llm_provider.check_capabilities(ctx)
            assert capabilities == {"test": "data"}

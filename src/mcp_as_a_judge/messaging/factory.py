"""
Messaging provider factory for smart provider selection.

This module implements the factory pattern for creating the appropriate
messaging provider based on capabilities and preferences. It automatically
detects MCP sampling capability and selects the best available provider.

The factory handles ALL message format decisions to ensure consistency.
"""

from typing import Any

from mcp.server.fastmcp import Context

from mcp_as_a_judge.messaging.converters import (
    mcp_messages_to_universal,
    validate_message_conversion,
)
from mcp_as_a_judge.messaging.interface import MessagingConfig, MessagingProvider
from mcp_as_a_judge.messaging.llm_api_provider import LLMAPIProvider
from mcp_as_a_judge.messaging.mcp_sampling_provider import MCPSamplingProvider


class MessagingProviderFactory:
    """Factory that creates the appropriate messaging provider based on capabilities.

    This factory implements smart provider selection:
    1. If prefer_sampling=True: Try MCP sampling first, then LLM API
    2. If prefer_sampling=False: Force LLM API only (no fallback)
    3. Raise error if no providers are available
    """

    @staticmethod
    def create_provider(ctx: Context, config: MessagingConfig) -> MessagingProvider:
        """Create the best available messaging provider.

        Args:
            ctx: MCP context
            config: Messaging configuration with prefer_sampling flag

        Returns:
            MessagingProvider instance

        Raises:
            RuntimeError: If no providers are available
        """
        # Create provider instances
        sampling_provider = MCPSamplingProvider(ctx)
        llm_provider = LLMAPIProvider()

        # Check availability
        sampling_available = sampling_provider.is_available()
        llm_available = llm_provider.is_available()

        # Select provider based on preference and availability
        if config.prefer_sampling:
            # Prefer sampling first, fall back to LLM API
            if sampling_available:
                return sampling_provider
            elif llm_available:
                return llm_provider
        else:
            # Force LLM API only (no fallback to sampling)
            if llm_available:
                return llm_provider

        # No providers available
        raise RuntimeError(
            f"No messaging providers available. "
            f"MCP sampling: {sampling_available}, LLM API: {llm_available}"
        )

    @staticmethod
    def get_provider_with_messages(
        ctx: Context, messages: list[Any], config: MessagingConfig
    ) -> tuple[MessagingProvider, list[Any]]:
        """
        Get the appropriate provider and convert messages to the correct format.

        This method makes ALL message format decisions at the factory level
        to ensure consistency throughout the system.

        Args:
            ctx: MCP context for capability detection
            messages: Input messages (typically SamplingMessage objects)
            config: Messaging configuration

        Returns:
            Tuple of (provider, formatted_messages) where formatted_messages
            are in the correct format for the selected provider
        """
        # Check provider availability
        sampling_provider = MCPSamplingProvider(ctx)
        llm_provider = LLMAPIProvider()

        sampling_available = sampling_provider.is_available()
        llm_available = llm_provider.is_available()

        if config.prefer_sampling:
            # Prefer sampling first, fall back to LLM API
            if sampling_available:
                # MCP sampling expects SamplingMessage objects directly
                return sampling_provider, messages
            elif llm_available:
                # LLM API expects universal Message objects
                universal_messages = mcp_messages_to_universal(messages)

                # Validate conversion
                if not validate_message_conversion(messages, universal_messages):
                    raise ValueError("Failed to convert messages to universal format")

                return llm_provider, universal_messages
        else:
            # Force LLM API only (no fallback to sampling)
            if llm_available:
                # LLM API expects universal Message objects
                universal_messages = mcp_messages_to_universal(messages)

                # Validate conversion
                if not validate_message_conversion(messages, universal_messages):
                    raise ValueError("Failed to convert messages to universal format")

                return llm_provider, universal_messages

        # No providers available
        raise RuntimeError(
            f"No messaging providers available. "
            f"MCP sampling: {sampling_available}, LLM API: {llm_available}"
        )

    @staticmethod
    def check_sampling_capability(ctx: Context) -> bool:
        """Check if the context has sampling capability enabled.

        Args:
            ctx: MCP context to check

        Returns:
            True if sampling is available, False otherwise
        """
        if ctx is None:
            return False  # type: ignore[unreachable]

        sampling_provider = MCPSamplingProvider(ctx)
        return sampling_provider.is_available()

    @staticmethod
    def check_llm_capability() -> bool:
        """Check if LLM API capability is available.

        Returns:
            True if LLM API is available, False otherwise
        """
        llm_provider = LLMAPIProvider()
        return llm_provider.is_available()

    @staticmethod
    def get_available_providers(ctx: Context) -> dict:
        """Get information about all available providers.

        Args:
            ctx: MCP context

        Returns:
            Dictionary with provider availability information
        """
        sampling_provider = MCPSamplingProvider(ctx)
        llm_provider = LLMAPIProvider()

        return {
            "mcp_sampling": {
                "available": sampling_provider.is_available(),
            },
            "llm_api": {
                "available": llm_provider.is_available(),
                "vendor_info": llm_provider.get_vendor_info(),
            },
        }

    @staticmethod
    def create_provider_with_fallback(
        ctx: Context, config: MessagingConfig, fallback_to_any: bool = True
    ) -> MessagingProvider | None:
        """Create provider with optional fallback to any available provider.

        Args:
            ctx: MCP context
            config: Messaging configuration
            fallback_to_any: If True, return any available provider even if
                           it doesn't match preferences

        Returns:
            MessagingProvider instance or None if none available
        """
        try:
            return MessagingProviderFactory.create_provider(ctx, config)
        except RuntimeError:
            if not fallback_to_any:
                return None

            # Try any available provider regardless of preference
            sampling_provider = MCPSamplingProvider(ctx)
            llm_provider = LLMAPIProvider()

            if sampling_provider.is_available():
                return sampling_provider
            elif llm_provider.is_available():
                return llm_provider

            return None

"""
Main LLM provider interface for the messaging layer.

This module provides the primary entry point for sending messages to AI providers.
It handles provider selection, message conversion, and provides a clean interface
for the rest of the application.
"""

from typing import Any

from mcp.server.fastmcp import Context

from mcp_as_a_judge.core.constants import DEFAULT_TEMPERATURE, MAX_TOKENS
from mcp_as_a_judge.messaging.converters import (
    mcp_messages_to_universal,  # re-exported for tests
    validate_message_conversion,  # re-exported for tests
)
from mcp_as_a_judge.messaging.factory import MessagingProviderFactory
from mcp_as_a_judge.messaging.interface import MessagingConfig


class LLMProvider:
    """Main interface for sending messages to LLM providers.

    This class provides a clean, high-level interface for sending messages
    to AI providers. It automatically handles provider selection, message
    conversion, and fallback logic.
    """

    async def send_message(
        self,
        messages: list[Any],  # MCP format from prompt_loader
        ctx: Context,
        max_tokens: int = MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        prefer_sampling: bool = True,
    ) -> str:
        """Send message using the best available provider.

        Args:
            messages: Messages in MCP format from prompt_loader
            ctx: MCP context
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation (0.0-1.0)
            prefer_sampling: Whether to prefer MCP sampling over LLM API

        Returns:
            Generated text response

        Raises:
            RuntimeError: If no providers are available
            ValueError: If message conversion fails
            Exception: If message generation fails
        """
        # Create configuration
        config = MessagingConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            prefer_sampling=prefer_sampling,
        )

        # Select provider using factory
        provider = MessagingProviderFactory.create_provider(ctx, config)

        # Convert messages to the correct format for the selected provider
        if provider.provider_type == "mcp_sampling":
            formatted_messages = messages
        else:
            # Convert MCP messages to universal format for LLM API providers
            formatted_messages = mcp_messages_to_universal(messages)
            if not validate_message_conversion(messages, formatted_messages):
                raise ValueError("Failed to convert messages to universal format")

        # Send message using the provider with correctly formatted messages
        try:
            if provider.provider_type == "mcp_sampling":
                # MCP sampling provider with SamplingMessage objects
                response = await provider.send_message_direct(  # type: ignore[attr-defined]
                    formatted_messages, config
                )
            else:
                # LLM API provider with universal Message objects
                response = await provider.send_message(formatted_messages, config)

            # Provider successfully used
            return str(response)

        except Exception as e:
            # If MCP sampling failed and LLM API is available, try fallback
            if (
                provider.provider_type == "mcp_sampling"
                and MessagingProviderFactory.check_llm_capability()
            ):
                # Check if this is an MCP sampling failure that should trigger fallback
                error_str = str(e).lower()
                is_mcp_failure = (
                    "method not found" in error_str
                    or "validation error" in error_str
                    or "sampling" in error_str
                    or "create_message" in error_str
                    or "mcperror" in error_str
                )

                if is_mcp_failure:
                    # Try LLM API fallback using factory
                    try:
                        # Force LLM API configuration for fallback
                        fallback_config = MessagingConfig(
                            max_tokens=config.max_tokens,
                            temperature=config.temperature,
                            prefer_sampling=False,  # Force LLM API
                        )

                        # Create LLM API provider and convert messages
                        fallback_provider = MessagingProviderFactory.create_provider(
                            ctx, fallback_config
                        )
                        if fallback_provider.provider_type == "mcp_sampling":
                            # Should not happen due to prefer_sampling=False, but guard anyway
                            fallback_messages = messages
                        else:
                            fallback_messages = mcp_messages_to_universal(messages)
                            if not validate_message_conversion(
                                messages, fallback_messages
                            ):
                                raise ValueError(
                                    "Failed to convert messages to universal format"
                                )

                        response = await fallback_provider.send_message(
                            fallback_messages, fallback_config
                        )
                        return str(response)

                    except Exception:  # nosec B110 - Intentional fallback when LLM API unavailable
                        # LLM API fallback failed, fall through to original error handling
                        # This is expected when no LLM API is configured
                        pass

            # Add context to the error
            provider_info = MessagingProviderFactory.get_available_providers(ctx)
            raise Exception(
                f"Failed to send message using {provider.provider_type}: {e}. "
                f"Provider info: {provider_info}. No messaging providers available"
            ) from e

    def check_capabilities(self, ctx: Context) -> dict:
        """Check what messaging capabilities are available.

        Args:
            ctx: MCP context

        Returns:
            Dictionary with capability information
        """
        return MessagingProviderFactory.get_available_providers(ctx)

    def is_sampling_available(self, ctx: Context) -> bool:
        """Check if MCP sampling is available.

        Args:
            ctx: MCP context

        Returns:
            True if MCP sampling is available, False otherwise
        """
        return MessagingProviderFactory.check_sampling_capability(ctx)

    def is_llm_api_available(self) -> bool:
        """Check if LLM API is available.

        Returns:
            True if LLM API is available, False otherwise
        """
        return MessagingProviderFactory.check_llm_capability()

    async def send_message_with_provider_preference(
        self,
        messages: list[Any],
        ctx: Context,
        provider_type: str,
        max_tokens: int = MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        """Send message with explicit provider preference.

        Args:
            messages: Messages in MCP format from prompt_loader
            ctx: MCP context
            provider_type: Preferred provider type ("mcp_sampling" or "llm_api")
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            Generated text response

        Raises:
            RuntimeError: If preferred provider is not available
            ValueError: If provider_type is invalid
        """
        if provider_type not in ["mcp_sampling", "llm_api"]:
            raise ValueError(f"Invalid provider_type: {provider_type}")

        prefer_sampling = provider_type == "mcp_sampling"

        return await self.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=max_tokens,
            temperature=temperature,
            prefer_sampling=prefer_sampling,
        )

    async def send_message_with_fallback(
        self,
        messages: list[Any],
        ctx: Context,
        max_tokens: int = MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        prefer_sampling: bool = True,
    ) -> str | None:
        """Send message with graceful fallback handling.

        This method attempts to send a message but returns None instead
        of raising an exception if no providers are available.

        Args:
            messages: Messages in MCP format from prompt_loader
            ctx: MCP context
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            prefer_sampling: Whether to prefer MCP sampling over LLM API

        Returns:
            Generated text response or None if no providers available
        """
        try:
            return await self.send_message(
                messages=messages,
                ctx=ctx,
                max_tokens=max_tokens,
                temperature=temperature,
                prefer_sampling=prefer_sampling,
            )
        except RuntimeError as e:
            if "No messaging providers available" in str(e):
                return None
            else:
                # Re-raise other runtime errors
                raise


# Global instance for easy access
llm_provider = LLMProvider()

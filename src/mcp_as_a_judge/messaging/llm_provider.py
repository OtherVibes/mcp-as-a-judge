"""
Main LLM provider interface for the messaging layer.

This module provides the primary entry point for sending messages to AI providers.
It handles provider selection, message conversion, and provides a clean interface
for the rest of the application.
"""

from typing import Any

from mcp.server.fastmcp import Context

from mcp_as_a_judge.messaging.converters import (
    mcp_messages_to_universal,
    validate_message_conversion,
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
        max_tokens: int = 1000,
        temperature: float = 0.1,
        top_p: float = 0.9,
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
            top_p=top_p,
            prefer_sampling=prefer_sampling,
        )

        # Get provider from factory
        provider = MessagingProviderFactory.create_provider(ctx, config)

        # Send message with appropriate format for each provider
        try:
            if provider.provider_type == "mcp_sampling":
                # For MCP sampling, pass original messages directly
                response = await provider.send_message_direct(messages, config)
            else:
                # For LLM API, convert to universal format first
                universal_messages = mcp_messages_to_universal(messages)

                # Validate conversion
                if not validate_message_conversion(messages, universal_messages):
                    raise ValueError("Failed to convert messages to universal format")

                response = await provider.send_message(universal_messages, config)

            # Provider successfully used

            return response

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
                    # Try LLM API fallback
                    try:
                        # Create LLM provider and try again
                        from mcp_as_a_judge.messaging.llm_api_provider import (
                            LLMAPIProvider,
                        )

                        llm_provider_instance = LLMAPIProvider()

                        # Convert to universal format for LLM API
                        universal_messages = mcp_messages_to_universal(messages)

                        if not validate_message_conversion(
                            messages, universal_messages
                        ):
                            raise ValueError(
                                "Failed to convert messages to universal format"
                            )

                        response = await llm_provider_instance.send_message(
                            universal_messages, config
                        )
                        return response

                    except Exception:
                        # LLM API fallback failed, fall through to original error handling
                        # This is expected when no LLM API is configured
                        pass

            # Add context to the error
            provider_info = MessagingProviderFactory.get_available_providers(ctx)
            raise Exception(
                f"Failed to send message using {provider.provider_type}: {e}. "
                f"Provider info: {provider_info}"
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
        max_tokens: int = 1000,
        temperature: float = 0.1,
        top_p: float = 0.9,
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
        max_tokens: int = 1000,
        temperature: float = 0.1,
        top_p: float = 0.9,
        prefer_sampling: bool = True,
        allow_any_provider: bool = True,
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
            allow_any_provider: If True, use any available provider as fallback

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

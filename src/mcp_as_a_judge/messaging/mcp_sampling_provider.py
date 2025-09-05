"""
MCP sampling provider for the messaging layer.

This module implements the MessagingProvider interface for MCP sampling,
which is the preferred method when available as it uses the client's
existing AI model without requiring separate API keys.
"""

from typing import Any

from mcp.server.fastmcp import Context

from mcp_as_a_judge.messaging.converters import messages_to_mcp_format
from mcp_as_a_judge.messaging.interface import (
    Message,
    MessagingConfig,
    MessagingProvider,
)


class MCPSamplingProvider(MessagingProvider):
    """MCP sampling provider - preferred when available.

    This provider uses the MCP client's sampling capability to generate
    responses using the client's existing AI model. This is preferred
    because it doesn't require separate API keys and uses the user's
    chosen AI model directly.
    """

    def __init__(self, context: Context):
        """Initialize the MCP sampling provider.

        Args:
            context: MCP context with session for sampling
        """
        self.context = context

    async def _send_message(
        self, messages: list[Message], config: MessagingConfig
    ) -> str:
        """Send messages via MCP sampling.

        Args:
            messages: List of universal Message objects
            config: Configuration for the request

        Returns:
            Generated text response

        Raises:
            Exception: If MCP sampling fails
        """
        # Convert to MCP format
        mcp_messages = messages_to_mcp_format(messages)

        # Send via MCP sampling
        result = await self.context.session.create_message(
            messages=mcp_messages,
            max_tokens=config.max_tokens,
        )

        # Extract text from response
        if hasattr(result.content, "type") and result.content.type == "text":
            return str(result.content.text)
        else:
            return str(result.content)

    async def send_message_direct(
        self, mcp_messages: list[Any], config: MessagingConfig
    ) -> str:
        """Send messages via MCP sampling using original MCP message format.

        Args:
            mcp_messages: List of MCP SamplingMessage objects (from prompt_loader)
            config: Configuration for the request

        Returns:
            Generated text response

        Raises:
            Exception: If MCP sampling fails
        """
        # Send via MCP sampling with original messages
        result = await self.context.session.create_message(
            messages=mcp_messages,
            max_tokens=config.max_tokens,
        )

        # Extract text from response
        if hasattr(result.content, "type") and result.content.type == "text":
            return str(result.content.text)
        else:
            return str(result.content)

    def is_available(self) -> bool:
        """Check if MCP sampling is available using proper MCP SDK method.

        This method uses the official MCP SDK way to check if the client
        supports sampling capability as recommended by DeepWiki.

        Returns:
            True if MCP sampling can be used, False otherwise
        """
        # Check if context exists
        if self.context is None:
            return False

        # Check if context has session
        if not hasattr(self.context, "session"):
            return False

        # Check if session exists
        if self.context.session is None:
            return False

        # Use the proper MCP SDK method to check client capability
        try:
            import mcp.types as types

            result = self.context.session.check_client_capability(
                types.ClientCapabilities(sampling=types.SamplingCapability())
            )
            return bool(result)
        except Exception:
            # If the check fails, fall back to basic method existence check
            has_method = hasattr(self.context.session, "create_message")
            is_callable = callable(
                getattr(self.context.session, "create_message", None)
            )
            return bool(has_method and is_callable)

    @property
    def provider_type(self) -> str:
        """Return provider type identifier.

        Returns:
            String identifier for this provider type
        """
        return "mcp_sampling"

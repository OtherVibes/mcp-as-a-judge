"""
Elicitation provider factory for smart provider selection.

This module implements the factory pattern for creating the appropriate
elicitation provider based on capabilities and preferences. It automatically
detects MCP elicitation capability and selects the best available provider.
"""

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from mcp_as_a_judge.elicitation.fallback_provider import FallbackElicitationProvider
from mcp_as_a_judge.elicitation.interface import ElicitationResult
from mcp_as_a_judge.elicitation.mcp_provider import MCPElicitationProvider


class ElicitationProviderFactory:
    """
    Unified elicitation provider that automatically selects the best available method.

    Similar to the messaging provider, this checks for elicitation capability and
    provides appropriate fallbacks when not available.
    """

    def __init__(self, prefer_elicitation: bool = True):
        """
        Initialize the elicitation provider factory.

        Args:
            prefer_elicitation: Whether to prefer MCP elicitation when available
        """
        self.prefer_elicitation = prefer_elicitation
        self._mcp_provider = MCPElicitationProvider()
        self._fallback_provider = FallbackElicitationProvider()

    async def elicit_user_input(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """
        Elicit user input using the best available method.

        Args:
            message: Message to display to the user
            schema: Pydantic model schema defining expected fields
            ctx: MCP context

        Returns:
            ElicitationResult with success status and data/message
        """

        # Check if MCP elicitation is available and preferred
        if self.prefer_elicitation and self._mcp_provider.check_capability(ctx):
            result = await self._mcp_provider.elicit(message, schema, ctx)

            # If MCP elicitation succeeds, return the result
            if result.success:
                return result

        # Use fallback provider
        return await self._fallback_provider.elicit(message, schema, ctx)

    def get_available_providers(self, ctx: Context) -> dict[str, dict[str, object]]:
        """Get information about all available providers.

        Args:
            ctx: MCP context for capability checking

        Returns:
            Dictionary with provider availability information
        """
        return {
            "mcp_elicitation": {
                "available": self._mcp_provider.check_capability(ctx),
                "provider_type": self._mcp_provider.provider_type,
            },
            "fallback_elicitation": {
                "available": True,  # Always available
                "provider_type": self._fallback_provider.provider_type,
            },
        }


# Global elicitation provider instance
elicitation_provider = ElicitationProviderFactory(prefer_elicitation=True)

"""
Elicitation provider for MCP as a Judge.

This module provides a unified interface for eliciting user input, with automatic
fallback when MCP elicitation is not available. Similar to the messaging provider,
it checks for elicitation capability and provides appropriate responses.
"""

from typing import Any

import mcp.types as types
from mcp.server.fastmcp import Context
from pydantic import BaseModel

from mcp_as_a_judge.models import ElicitationFallbackUserVars
from mcp_as_a_judge.prompt_loader import prompt_loader


class ElicitationResult:
    """Result from elicitation attempt."""

    def __init__(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        message: str | None = None,
    ):
        self.success = success
        self.data = data or {}
        self.message = message or ""


class BaseElicitationProvider:
    """Base class for elicitation providers."""

    async def elicit(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """Elicit user input using this provider.

        This is the public interface method that can contain common logic
        for all providers (logging, validation, etc.) and calls the internal
        implementation method.
        """
        # Add any common pre-processing logic here
        # (logging, validation, metrics, etc.)

        # Call the internal implementation
        result = await self._elicit(message, schema, ctx)

        # Add any common post-processing logic here
        # (logging, error handling, metrics, etc.)

        return result

    async def _elicit(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """Internal elicitation implementation - override this in subclasses."""
        raise NotImplementedError


class MCPElicitationProvider(BaseElicitationProvider):
    """MCP elicitation provider using ctx.elicit()."""

    async def _elicit(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """Elicit user input using MCP elicitation."""
        try:
            elicit_result = await ctx.elicit(message=message, schema=schema)

            if elicit_result.action == "accept" and elicit_result.data:
                # Convert Pydantic model to dictionary
                if hasattr(elicit_result.data, "model_dump"):
                    data = elicit_result.data.model_dump()
                elif isinstance(elicit_result.data, dict):
                    data = elicit_result.data
                else:
                    # Handle unexpected data types (like boolean, string, etc.)
                    data = {"user_input": str(elicit_result.data)}

                return ElicitationResult(success=True, data=data)
            else:
                return ElicitationResult(
                    success=False,
                    message="User cancelled or rejected the elicitation request",
                )

        except Exception as e:
            return ElicitationResult(
                success=False, message=f"MCP elicitation failed: {e!s}"
            )


class FallbackElicitationProvider(BaseElicitationProvider):
    """Fallback provider that returns a message for the AI assistant to prompt the user."""

    async def _elicit(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """Generate a fallback message for the AI assistant to prompt the user."""

        # Extract field information from the schema
        required_fields = []
        optional_fields = []

        for field_name, field_info in schema.model_fields.items():
            field_desc = field_info.description or field_name.replace("_", " ").title()

            if field_info.is_required():
                required_fields.append(f"- **{field_desc}**")
            else:
                optional_fields.append(f"- **{field_desc}**")

        # Create template variables
        template_vars = ElicitationFallbackUserVars(
            original_message=message,
            required_fields=required_fields,
            optional_fields=optional_fields,
        )

        # Generate fallback message using prompt template
        fallback_message = prompt_loader.render_prompt(
            "user/elicitation_fallback.md", **template_vars.model_dump()
        )

        return ElicitationResult(success=False, message=fallback_message)


class ElicitationProvider:
    """
    Unified elicitation provider that automatically selects the best available method.

    Similar to the messaging provider, this checks for elicitation capability and
    provides appropriate fallbacks when not available.
    """

    def __init__(self, prefer_elicitation: bool = True):
        """
        Initialize the elicitation provider.

        Args:
            prefer_elicitation: Whether to prefer MCP elicitation when available
        """
        self.prefer_elicitation = prefer_elicitation
        self._mcp_provider = MCPElicitationProvider()
        self._fallback_provider = FallbackElicitationProvider()

    def _check_elicitation_capability(self, ctx: Context) -> bool:
        """
        Check if MCP elicitation is available.

        Args:
            ctx: MCP context

        Returns:
            True if elicitation is available, False otherwise
        """
        try:
            # Check if the client declared elicitation capability during initialization
            result = ctx.session.check_client_capability(
                types.ClientCapabilities(elicitation=types.ElicitationCapability())
            )
            return bool(result)
        except Exception:
            # Fallback to basic method check if session capability check fails
            return hasattr(ctx, "elicit") and callable(ctx.elicit)

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
        if self.prefer_elicitation and self._check_elicitation_capability(ctx):
            result = await self._mcp_provider.elicit(message, schema, ctx)

            # If MCP elicitation succeeds, return the result
            if result.success:
                return result

        # Use fallback provider
        return await self._fallback_provider.elicit(message, schema, ctx)


# Global elicitation provider instance
elicitation_provider = ElicitationProvider(prefer_elicitation=True)

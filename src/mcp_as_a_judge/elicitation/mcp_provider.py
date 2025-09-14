"""
MCP elicitation provider using ctx.elicit().

This provider uses the native MCP elicitation capability when available.
"""

import mcp.types as types
from mcp.server.fastmcp import Context
from pydantic import BaseModel

from mcp_as_a_judge.elicitation.interface import ElicitationProvider, ElicitationResult


class MCPElicitationProvider(ElicitationProvider):
    """MCP elicitation provider using ctx.elicit()."""

    @property
    def provider_type(self) -> str:
        """Return the provider type identifier."""
        return "mcp_elicitation"

    async def _elicit(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """Elicit user input using MCP elicitation.

        Args:
            message: Message to display to the user
            schema: Pydantic model schema defining expected fields
            ctx: MCP context

        Returns:
            ElicitationResult with success status and data/message
        """
        try:
            elicit_result = await ctx.elicit(message=message, schema=schema)

            if elicit_result.action == "accept" and elicit_result.data:
                # Convert Pydantic model to dictionary
                if hasattr(elicit_result.data, "model_dump"):
                    data = elicit_result.data.model_dump(exclude_none=True)
                elif isinstance(elicit_result.data, dict):  # type: ignore[unreachable]
                    data = elicit_result.data  # type: ignore[unreachable]
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

    def check_capability(self, ctx: Context) -> bool:
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

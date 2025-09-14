"""
Fallback elicitation provider that returns a message for the AI assistant.

This provider generates a structured message that the AI assistant can use
to prompt the user when MCP elicitation is not available.
"""

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from mcp_as_a_judge.elicitation.interface import ElicitationProvider, ElicitationResult
from mcp_as_a_judge.models import ElicitationFallbackUserVars
from mcp_as_a_judge.prompting.loader import prompt_loader


class FallbackElicitationProvider(ElicitationProvider):
    """Fallback provider that returns a message for the AI assistant to prompt the user."""

    @property
    def provider_type(self) -> str:
        """Return the provider type identifier."""
        return "fallback_elicitation"

    async def _elicit(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """Generate a fallback message for the AI assistant to prompt the user.

        Args:
            message: Original message to display to the user
            schema: Pydantic model schema defining expected fields
            ctx: MCP context

        Returns:
            ElicitationResult with success=False and a formatted message
        """

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
            "user/elicitation_fallback.md",
            **template_vars.model_dump(exclude_none=True),
        )

        return ElicitationResult(success=False, message=fallback_message)

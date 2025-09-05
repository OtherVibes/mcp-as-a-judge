"""
Tool description provider module.

This module provides the main interface for accessing tool descriptions
through the factory pattern. It exports the global tool_description_provider
instance that the server uses.
"""

from mcp_as_a_judge.tool_description.factory import (
    tool_description_provider,
    tool_description_provider_factory,
)

# Export the global instances for backward compatibility and easy access
__all__ = [
    "tool_description_provider",
    "tool_description_provider_factory",
]

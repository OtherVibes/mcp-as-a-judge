"""
Elicitation provider package.

This package provides a factory pattern for creating elicitation providers
that handle user input elicitation through various methods (MCP elicitation,
fallback prompts, etc.).
"""

from mcp_as_a_judge.elicitation.factory import (
    ElicitationProviderFactory,
    elicitation_provider,
)
from mcp_as_a_judge.elicitation.fallback_provider import FallbackElicitationProvider
from mcp_as_a_judge.elicitation.interface import ElicitationProvider, ElicitationResult
from mcp_as_a_judge.elicitation.mcp_provider import MCPElicitationProvider

__all__ = [
    "ElicitationProvider",
    "ElicitationProviderFactory",
    "ElicitationResult",
    "FallbackElicitationProvider",
    "MCPElicitationProvider",
    "elicitation_provider",
]

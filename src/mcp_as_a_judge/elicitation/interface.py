"""
Interface definitions for elicitation providers.

This module defines the abstract base classes and data structures
used by all elicitation provider implementations.
"""

from abc import ABC, abstractmethod
from typing import Any

from mcp.server.fastmcp import Context
from pydantic import BaseModel


class ElicitationResult:
    """Result from elicitation attempt."""

    def __init__(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        message: str | None = None,
    ):
        """Initialize elicitation result.

        Args:
            success: Whether the elicitation was successful
            data: Data returned from successful elicitation
            message: Message for failed elicitation or additional info
        """
        self.success = success
        self.data = data or {}
        self.message = message or ""


class ElicitationProvider(ABC):
    """Abstract base class for elicitation providers."""

    async def elicit(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """Elicit user input using this provider.

        This is the public interface method that can contain common logic
        for all providers (logging, validation, etc.) and calls the internal
        implementation method.

        Args:
            message: Message to display to the user
            schema: Pydantic model schema defining expected fields
            ctx: MCP context

        Returns:
            ElicitationResult with success status and data/message
        """
        # Add any common pre-processing logic here
        # (logging, validation, metrics, etc.)

        # Call the internal implementation
        result = await self._elicit(message, schema, ctx)

        # Add any common post-processing logic here
        # (logging, error handling, metrics, etc.)

        return result

    @abstractmethod
    async def _elicit(
        self, message: str, schema: type[BaseModel], ctx: Context
    ) -> ElicitationResult:
        """Internal elicitation implementation - override this in subclasses.

        Args:
            message: Message to display to the user
            schema: Pydantic model schema defining expected fields
            ctx: MCP context

        Returns:
            ElicitationResult with success status and data/message
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Return the provider type identifier."""
        raise NotImplementedError

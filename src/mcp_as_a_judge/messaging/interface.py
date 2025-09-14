"""
Abstract messaging interface for MCP as a Judge.

This module defines the core interfaces and data models for the messaging layer,
providing a unified way to interact with different AI providers.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from mcp_as_a_judge.core.constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    MAX_TOKENS,
)


class Message(BaseModel):
    """Universal message format for the messaging layer.

    This standardized format allows conversion between different
    provider-specific message formats (MCP, OpenAI, etc.).
    """

    role: str = Field(description="Message role (system, user, assistant)")
    content: str = Field(description="Message content text")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata for provider-specific features"
    )


class MessagingConfig(BaseModel):
    """Configuration for messaging providers.

    This configuration controls how messages are sent and which
    providers are preferred. Defaults are optimized for coding tasks
    with low temperature (0.1) for deterministic, precise responses.
    """

    max_tokens: int = Field(
        default=MAX_TOKENS, description="Maximum tokens to generate"
    )
    temperature: float = Field(
        default=DEFAULT_TEMPERATURE,
        ge=0.0,
        le=1.0,
        description="Temperature for generation (0.0-1.0) - Low for coding tasks",
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT, description="Timeout in seconds for requests"
    )
    prefer_sampling: bool = Field(
        default=True,
        description="Provider selection: True=prefer MCP sampling (fallback to LLM API), False=force LLM API only",
    )


class MessagingProvider(ABC):
    """Abstract base class for all messaging providers.

    This interface ensures consistent behavior across different
    AI providers (MCP sampling, LLM APIs, etc.).
    """

    async def send_message(
        self, messages: list[Message], config: MessagingConfig
    ) -> str:
        """Send messages and return response text.

        This is the public interface method that can contain common logic
        for all providers (logging, validation, etc.) and calls the internal
        implementation method.

        Args:
            messages: List of messages to send
            config: Configuration for the request

        Returns:
            Generated text response

        Raises:
            Exception: If the provider fails to generate a response
        """
        # Add any common pre-processing logic here
        # (logging, validation, metrics, etc.)

        # Call the internal implementation
        result = await self._send_message(messages, config)

        # Add any common post-processing logic here
        # (logging, error handling, metrics, etc.)

        return result

    @abstractmethod
    async def _send_message(
        self, messages: list[Message], config: MessagingConfig
    ) -> str:
        """Internal message sending implementation - override this in subclasses.

        Args:
            messages: List of messages to send
            config: Configuration for the request

        Returns:
            Generated text response

        Raises:
            Exception: If the provider fails to generate a response
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available.

        Returns:
            True if the provider can be used, False otherwise
        """
        pass

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Return provider type identifier.

        Returns:
            String identifier for this provider type
        """
        pass

    def __str__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}(type={self.provider_type}, available={self.is_available()})"

"""
LLM API provider for the messaging layer.

This module implements the MessagingProvider interface for direct LLM API calls
using the existing llm_client infrastructure. This serves as a fallback when
MCP sampling is not available.
"""

from mcp_as_a_judge.core.constants import DEFAULT_TEMPERATURE, MAX_TOKENS
from mcp_as_a_judge.llm.llm_client import llm_manager
from mcp_as_a_judge.llm.llm_integration import load_llm_config_from_env
from mcp_as_a_judge.messaging.converters import messages_to_llm_format
from mcp_as_a_judge.messaging.interface import (
    Message,
    MessagingConfig,
    MessagingProvider,
)


class LLMAPIProvider(MessagingProvider):
    """LLM API provider - fallback when MCP sampling not available.

    This provider uses direct LLM API calls through the existing llm_client
    infrastructure. It supports multiple LLM providers (OpenAI, Anthropic,
    Google, etc.) through LiteLLM.
    """

    def __init__(self) -> None:
        """Initialize the LLM API provider.

        Automatically configures the LLM manager from environment if not already configured.
        """
        self._ensure_configured()

    def _ensure_configured(self) -> None:
        """Ensure LLM manager is configured from environment."""
        if not llm_manager.is_available():
            config = load_llm_config_from_env()
            if config:
                llm_manager.configure(config)

    async def _send_message(
        self, messages: list[Message], config: MessagingConfig
    ) -> str:
        """Send messages via LLM API.

        Args:
            messages: List of universal Message objects
            config: Configuration for the request

        Returns:
            Generated text response

        Raises:
            RuntimeError: If LLM client is not configured
            Exception: If LLM API call fails
        """
        # Get the LLM client
        client = llm_manager.get_client()
        if not client:
            raise RuntimeError(
                "LLM client not configured. Please set an API key environment variable."
            )

        # Convert to LLM API format
        llm_messages = messages_to_llm_format(messages)

        # Send via LLM API
        response = await client.generate_text(
            messages=llm_messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

        return response

    def is_available(self) -> bool:
        """Check if LLM API client is available.

        Returns:
            True if LLM client is configured and available, False otherwise
        """
        return llm_manager.is_available()

    @property
    def provider_type(self) -> str:
        """Return provider type identifier.

        Returns:
            String identifier for this provider type
        """
        return "llm_api"

    def get_vendor_info(self) -> dict:
        """Get information about the configured LLM vendor.

        Returns:
            Dictionary with vendor information, or empty dict if not available
        """
        client = llm_manager.get_client()
        if not client or not hasattr(client, "config"):
            return {}

        config = client.config
        return {
            "vendor": getattr(config, "vendor", "unknown"),
            "model_name": getattr(config, "model_name", "unknown"),
            "max_tokens": getattr(config, "max_tokens", MAX_TOKENS),
            "temperature": getattr(config, "temperature", DEFAULT_TEMPERATURE),
        }

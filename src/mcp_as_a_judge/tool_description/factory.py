"""
Tool description provider factory for smart provider selection.

This module implements the factory pattern for creating the appropriate
tool description provider. Currently returns only the local storage implementation,
but can be extended to support additional providers in the future.
"""

from mcp_as_a_judge.tool_description.interface import ToolDescriptionProvider
from mcp_as_a_judge.tool_description.local_storage_provider import LocalStorageProvider


class ToolDescriptionProviderFactory:
    """Factory that creates the appropriate tool description provider.

    Currently returns only the local storage provider, but this factory
    can be extended in the future to support additional provider types
    (remote APIs, databases, etc.) with smart selection logic.
    """

    @staticmethod
    def create_provider() -> ToolDescriptionProvider:
        """Create the tool description provider.

        Currently returns the local storage provider as the only implementation.
        Future versions can add configuration parameters and smart selection logic.

        Returns:
            ToolDescriptionProvider instance
        """
        return LocalStorageProvider()

    @staticmethod
    def get_available_providers() -> dict[str, dict[str, object]]:
        """Get information about all available providers.

        Returns:
            Dictionary with provider availability information
        """
        local_provider = LocalStorageProvider()

        return {
            "local_storage": {
                "available": True,
                "provider_type": local_provider.provider_type,
            }
        }


# Global factory instance for easy access
tool_description_provider_factory = ToolDescriptionProviderFactory()

# Global provider instance for easy access (following existing pattern)
tool_description_provider = tool_description_provider_factory.create_provider()

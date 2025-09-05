"""
Interface for tool description providers.

This module defines the abstract base class that all tool description providers
must implement, ensuring consistent behavior across different provider types.
"""

from abc import ABC, abstractmethod


class ToolDescriptionProvider(ABC):
    """Abstract base class for all tool description providers.

    This interface ensures consistent behavior across different
    tool description providers (local storage, remote APIs, etc.).
    """

    @abstractmethod
    def get_description(self, tool_name: str) -> str:
        """Get tool description for the specified tool.

        Args:
            tool_name: Name of the tool (e.g., 'build_workflow')

        Returns:
            Tool description string

        Raises:
            FileNotFoundError: If description file doesn't exist
        """
        pass

    @abstractmethod
    def get_available_tools(self) -> list[str]:
        """Get list of available tool names.

        Returns:
            List of tool names that have descriptions available
        """
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear any cached descriptions.

        Useful for testing or when description files are updated at runtime.
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

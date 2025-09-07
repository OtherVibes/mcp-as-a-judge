"""
Database factory for creating database providers.

This module provides a factory function to create the appropriate
database provider based on configuration.
"""

from typing import Any, ClassVar, cast

from mcp_as_a_judge.db.db_config import Config, get_database_provider_from_url
from mcp_as_a_judge.db.interface import ConversationHistoryDB
from mcp_as_a_judge.db.providers import SQLiteProvider


class DatabaseFactory:
    """Factory for creating database providers."""

    _providers: ClassVar[dict[str, Any]] = {
        "in_memory": SQLiteProvider,  # SQLModel SQLite in-memory (:memory: or empty URL)
        "sqlite": SQLiteProvider,  # SQLModel SQLite file-based storage
        # Future providers can be added here:
        # "postgresql": PostgreSQLProvider,
        # "mysql": MySQLProvider,
    }

    @classmethod
    def create_provider(cls, config: Config) -> ConversationHistoryDB:
        """
        Create a database provider based on configuration.

        Args:
            config: Application configuration

        Returns:
            ConversationHistoryDB instance

        Raises:
            ValueError: If provider is not supported
        """
        # Determine provider from database URL
        provider_name = get_database_provider_from_url(config.database.url)

        # Get provider class
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unsupported database provider: {provider_name} (detected from URL: '{config.database.url}'). "
                f"Available providers: {available}"
            )

        provider_class = cls._providers[provider_name]

        # Create provider instance - call concrete implementation constructor
        # All current providers accept max_session_records and url parameters
        return cast(
            ConversationHistoryDB,
            provider_class(
                max_session_records=config.database.max_session_records,
                url=config.database.url,
            ),
        )

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())

    # Not in use - option to register additional providers
    @classmethod
    def register_provider(
        cls, name: str, provider_class: type[ConversationHistoryDB]
    ) -> None:
        """
        Register a new database provider.

        Args:
            name: Provider name (e.g., 'sqlite', 'postgresql')
            provider_class: Provider class that implements ConversationHistoryDB
        """
        cls._providers[name] = provider_class


# Convenience function
def create_database_provider(config: Config) -> ConversationHistoryDB:
    """
    Create a database provider based on configuration.

    Args:
        config: Application configuration

    Returns:
        ConversationHistoryDB instance
    """
    return DatabaseFactory.create_provider(config)

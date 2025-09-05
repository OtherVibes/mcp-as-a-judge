"""
Database factory for creating database providers.

This module provides a factory function to create the appropriate
database provider based on configuration.
"""

from typing import Dict, Type

from ..config import Config, get_database_provider_from_url
from .interface import ConversationHistoryDB
from .providers import InMemoryProvider


class DatabaseFactory:
    """Factory for creating database providers."""
    
    _providers: Dict[str, Type[ConversationHistoryDB]] = {
        "in_memory": InMemoryProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[ConversationHistoryDB]) -> None:
        """
        Register a new database provider.
        
        Args:
            name: Provider name (e.g., 'sqlite', 'postgresql')
            provider_class: Provider class that implements ConversationHistoryDB
        """
        cls._providers[name] = provider_class
    
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
        # Determine provider from config
        provider_name = config.database.provider
        
        # If provider is auto, determine from URL
        if provider_name == "auto":
            provider_name = get_database_provider_from_url(config.database.url)
        
        # Get provider class
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unsupported database provider: {provider_name}. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._providers[provider_name]
        
        # Create provider instance
        if provider_name == "in_memory":
            return provider_class(
                max_context_records=config.database.max_context_records
            )
        else:
            # For future SQL providers, pass connection URL and config
            return provider_class(
                url=config.database.url,
                max_context_records=config.database.max_context_records
            )
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())


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

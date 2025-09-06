"""
Database abstraction layer for MCP as a Judge.

This module provides database interfaces and providers for storing
conversation history and tool interactions.
"""

from .factory import DatabaseFactory, create_database_provider
from .interface import ConversationHistoryDB, ConversationRecord
from .providers import SQLiteProvider

__all__ = [
    "ConversationHistoryDB",
    "ConversationRecord",
    "SQLiteProvider",
    "DatabaseFactory",
    "create_database_provider"
]

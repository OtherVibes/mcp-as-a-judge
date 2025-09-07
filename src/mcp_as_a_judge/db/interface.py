"""
Database interface for conversation history storage.

This module defines the abstract interface that all database providers
must implement for storing and retrieving conversation history.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from sqlmodel import Field, SQLModel


class ConversationRecord(SQLModel, table=True):
    """SQLModel for conversation history records."""

    __tablename__ = "conversation_history"

    id: str | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    source: str  # tool name
    input: str  # tool input query
    output: str  # tool output string
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, index=True
    )  # when the record was created


class ConversationHistoryDB(ABC):
    """Abstract interface for conversation history database operations."""

    @abstractmethod
    def __init__(
        self, max_context_records: int = 20, retention_days: int = 1, url: str = ""
    ) -> None:
        """
        Initialize the database provider.

        Args:
            max_context_records: Maximum number of conversation records to keep per session
            retention_days: Number of days to keep conversation records before deletion
            url: Database connection URL
        """
        pass

    @abstractmethod
    async def save_conversation(
        self, session_id: str, source: str, input_data: str, output: str
    ) -> str:
        """
        Save a conversation record to the database.

        Args:
            session_id: Session identifier from AI agent
            source: Tool name that generated this record
            input_data: Tool input query
            output: Tool output string

        Returns:
            The ID of the created record
        """
        pass

    @abstractmethod
    async def get_session_conversations(
        self, session_id: str, limit: int | None = None
    ) -> list[ConversationRecord]:
        """
        Retrieve all conversation records for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of records to return (most recent first)

        Returns:
            List of ConversationRecord objects
        """
        pass



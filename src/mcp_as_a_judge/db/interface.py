"""
Database interface for conversation history storage.

This module defines the abstract interface that all database providers
must implement for storing and retrieving conversation history.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationRecord(BaseModel):
    """Model for conversation history records."""

    id: str
    session_id: str
    source: str  # tool name
    input: str  # tool input query
    output: str  # tool output string
    timestamp: datetime = Field(default_factory=datetime.utcnow)  # when the record was created


class ConversationHistoryDB(ABC):
    """Abstract interface for conversation history database operations."""

    @abstractmethod
    async def save_conversation(
        self,
        session_id: str,
        source: str,
        input_data: str,
        output: str
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
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationRecord]:
        """
        Retrieve all conversation records for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of records to return (most recent first)

        Returns:
            List of ConversationRecord objects
        """
        pass

    # TEST-ONLY METHODS
    # The following methods are used only by tests, not by application code
    def clear_session(self, session_id: str) -> int:
        """
        Clear all conversation records for a session.

        **TEST-ONLY METHOD** - Used exclusively by tests for cleanup.
        """
        raise NotImplementedError("Test-only method")

    def get_stats(self) -> dict[str, int]:
        """
        Get statistics about the database storage.

        **TEST-ONLY METHOD** - Used exclusively by tests for verification.
        """
        raise NotImplementedError("Test-only method")

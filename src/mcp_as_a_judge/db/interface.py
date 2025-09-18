"""
Database interface for conversation history storage.

This module defines the abstract interface that all database providers
must implement for storing and retrieving conversation history.
"""

import time
from abc import ABC, abstractmethod

from sqlmodel import Field, SQLModel


class ConversationRecord(SQLModel, table=True):
    """SQLModel for conversation history records."""

    __tablename__ = "conversation_history"

    id: str | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    source: str  # tool name
    input: str  # tool input query
    output: str  # tool output string
    tokens: int = Field(
        default=0
    )  # combined token count for input + output (1 token ≈ 4 characters)
    timestamp: int = Field(
        default_factory=lambda: int(time.time()), index=True
    )  # when the record was created (epoch seconds)


class ConversationHistoryDB(ABC):
    """Abstract interface for conversation history database operations."""

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

    @abstractmethod
    async def get_recent_sessions(self, limit: int = 10) -> list[tuple[str, int]]:
        """
        Retrieve most recently active sessions.

        Args:
            limit: Maximum number of session IDs to return

        Returns:
            List of tuples: (session_id, last_activity_timestamp), ordered by most recent first
        """
        pass

    @abstractmethod
    async def delete_previous_plan(self, session_id: str) -> None:
        """
        Delete all previous judge_coding_plan records except the most recent one.

        This method removes all but the last conversation record with source='judge_coding_plan'
        for the given session to avoid keeping multiple failed plan attempts.

        Args:
            session_id: Session identifier
        """
        pass

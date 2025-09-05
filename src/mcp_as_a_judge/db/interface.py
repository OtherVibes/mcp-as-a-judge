"""
Database interface for conversation history storage.

This module defines the abstract interface that all database providers
must implement for storing and retrieving conversation history.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationRecord(BaseModel):
    """Model for conversation history records."""

    id: str
    session_id: str
    source: str  # tool name
    input: str  # tool input query
    context: List[str]  # JSON array of conversation IDs for historical context
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
        context: List[str],
        output: str
    ) -> str:
        """
        Save a conversation record to the database.
        
        Args:
            session_id: Session identifier from AI agent
            source: Tool name that generated this record
            input_data: Tool input query
            context: List of conversation IDs for historical context
            output: Tool output string
            
        Returns:
            The ID of the created record
        """
        pass
    
    @abstractmethod
    async def get_conversation(self, record_id: str) -> Optional[ConversationRecord]:
        """
        Retrieve a conversation record by ID.
        
        Args:
            record_id: The ID of the record to retrieve
            
        Returns:
            ConversationRecord if found, None otherwise
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
    
    @abstractmethod
    async def get_recent_conversations(
        self, 
        session_id: str, 
        count: int = 10
    ) -> List[str]:
        """
        Get the most recent conversation IDs for context building.
        
        Args:
            session_id: Session identifier
            count: Number of recent conversation IDs to return
            
        Returns:
            List of conversation IDs (most recent first)
        """
        pass
    
    @abstractmethod
    async def delete_conversation(self, record_id: str) -> bool:
        """
        Delete a conversation record.
        
        Args:
            record_id: The ID of the record to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def clear_session(self, session_id: str) -> int:
        """
        Clear all conversation records for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of records deleted
        """
        pass

"""
Database test utilities for MCP as a Judge.

This module provides test-only utilities for database operations that should not
be part of the production source code.
"""

from sqlmodel import Session, select

from mcp_as_a_judge.db.interface import ConversationHistoryDB, ConversationRecord
from mcp_as_a_judge.db.providers.sqlite_provider import SQLiteProvider


class DatabaseTestUtils:
    """Test utilities for database operations."""

    @staticmethod
    async def clear_session(db: ConversationHistoryDB, session_id: str) -> int:
        """
        Clear all conversation records for a session.

        Args:
            db: Database provider instance
            session_id: Session identifier to clear

        Returns:
            Number of records deleted
        """
        if isinstance(db, SQLiteProvider):
            with Session(db.engine) as session:
                stmt = select(ConversationRecord).where(
                    ConversationRecord.session_id == session_id
                )
                records = session.exec(stmt).all()

                for record in records:
                    session.delete(record)

                session.commit()
                return len(records)
        else:
            raise NotImplementedError(f"clear_session not implemented for {type(db)}")

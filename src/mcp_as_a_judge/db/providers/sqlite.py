"""
SQLModel-based SQLite database provider for conversation history.

This provider uses SQLModel with SQLAlchemy for type-safe database operations.
It supports both in-memory (:memory:) and file-based SQLite storage.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, asc, desc, select

from mcp_as_a_judge.logging_config import get_logger

from ..interface import ConversationHistoryDB, ConversationRecord

# Set up logger
logger = get_logger(__name__)


class SQLiteProvider(ConversationHistoryDB):
    """
    SQLModel-based SQLite database provider for conversation history.

    Supports both in-memory (:memory:) and file-based SQLite storage
    depending on the URL configuration.

    Features:
    - SQLModel with SQLAlchemy for type safety
    - In-memory or file-based SQLite storage
    - LRU cleanup per session
    - Time-based cleanup (configurable retention)
    - Session-based conversation retrieval
    """

    def __init__(
        self, max_context_records: int = 20, retention_days: int = 1, url: str = ""
    ) -> None:
        """Initialize the SQLModel SQLite database with LRU and time-based cleanup."""
        # Parse URL to get SQLite connection string
        connection_string = self._parse_sqlite_url(url)

        # Create SQLAlchemy engine
        self.engine = create_engine(
            connection_string,
            echo=False,  # Set to True for SQL debugging
            connect_args={"check_same_thread": False}
            if ":memory:" in connection_string
            else {},
        )

        self._max_context_records = max_context_records
        self._retention_days = retention_days
        self._last_cleanup_time = datetime.utcnow()

        # Create tables
        self._create_tables()

        logger.info(
            f"🗄️ SQLModel SQLite provider initialized: {connection_string}, "
            f"max_records={max_context_records}, retention_days={retention_days}"
        )

    def _parse_sqlite_url(self, url: str) -> str:
        """Parse database URL to SQLite connection string."""
        if not url or url == ":memory:":
            return "sqlite:///:memory:"
        elif url == "sqlite://:memory:":
            # Fix the malformed SQLite in-memory URL
            return "sqlite:///:memory:"
        elif url.startswith("sqlite://") or url.startswith("sqlite:///"):
            return url
        else:
            # Assume it's a file path
            return f"sqlite:///{url}"

    def _create_tables(self) -> None:
        """Create database tables using SQLModel."""
        SQLModel.metadata.create_all(self.engine)
        logger.info("📋 Created conversation_history table with SQLModel")

    def _cleanup_old_records(self) -> int:
        """
        Remove records older than retention_days.
        This runs once per day to avoid excessive cleanup operations.
        """
        # Only run cleanup once per day
        if (datetime.utcnow() - self._last_cleanup_time).days < 1:
            return 0

        cutoff_date = datetime.utcnow() - timedelta(days=self._retention_days)

        with Session(self.engine) as session:
            # Count old records
            old_count_stmt = select(ConversationRecord).where(
                ConversationRecord.timestamp < cutoff_date
            )
            old_records = session.exec(old_count_stmt).all()
            old_count = len(old_records)

            if old_count == 0:
                logger.info(
                    f"🧹 Daily cleanup: No records older than {self._retention_days} days"
                )
                self._last_cleanup_time = datetime.utcnow()
                return 0

            # Delete old records
            for record in old_records:
                session.delete(record)

            session.commit()

            # Reset cleanup tracking
            self._last_cleanup_time = datetime.utcnow()

            logger.info(
                f"🧹 Daily cleanup: Deleted {old_count} records older than {self._retention_days} days"
            )
            return old_count

    def _cleanup_old_messages(self, session_id: str) -> int:
        """
        Remove old messages from a session using LRU (Least Recently Used) strategy.
        Keeps only the most recent max_context_records messages per session.
        """
        with Session(self.engine) as session:
            # Count current messages in session
            count_stmt = select(ConversationRecord).where(
                ConversationRecord.session_id == session_id
            )
            current_records = session.exec(count_stmt).all()
            current_count = len(current_records)

            logger.info(
                f"🧹 LRU cleanup check for session {session_id}: {current_count} records "
                f"(max: {self._max_context_records})"
            )

            if current_count <= self._max_context_records:
                logger.info("   No cleanup needed - within limits")
                return 0

            # Get oldest records to remove
            records_to_remove = current_count - self._max_context_records
            oldest_stmt = (
                select(ConversationRecord)
                .where(ConversationRecord.session_id == session_id)
                .order_by(asc(ConversationRecord.timestamp))
                .limit(records_to_remove)
            )
            old_records = session.exec(oldest_stmt).all()

            logger.info(f"🗑️ Removing {len(old_records)} oldest records:")
            for i, record in enumerate(old_records, 1):
                logger.info(
                    f"   {i}. ID: {record.id[:8] if record.id else 'None'}... | "
                    f"Source: {record.source} | Timestamp: {record.timestamp}"
                )

            # Remove the old messages
            for record in old_records:
                session.delete(record)

            session.commit()

            logger.info(
                f"✅ LRU cleanup completed: removed {len(old_records)} records from session {session_id}"
            )
            return len(old_records)

    async def save_conversation(
        self, session_id: str, source: str, input_data: str, output: str
    ) -> str:
        """Save a conversation record to SQLite database with LRU cleanup."""
        record_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        logger.info(
            f"💾 Saving conversation to SQLModel SQLite DB: record {record_id} "
            f"for session {session_id}, source {source} at {timestamp}"
        )

        # Create new record
        record = ConversationRecord(
            id=record_id,
            session_id=session_id,
            source=source,
            input=input_data,
            output=output,
            timestamp=timestamp,
        )

        with Session(self.engine) as session:
            session.add(record)
            session.commit()

        logger.info("✅ Successfully inserted record into conversation_history table")

        # Daily cleanup: run once per day to remove old records
        self._cleanup_old_records()

        # Always perform LRU cleanup for this session (lightweight)
        self._cleanup_old_messages(session_id)

        return record_id

    async def get_session_conversations(
        self, session_id: str, limit: int | None = None
    ) -> list[ConversationRecord]:
        """Retrieve all conversation records for a session."""
        with Session(self.engine) as session:
            stmt = (
                select(ConversationRecord)
                .where(ConversationRecord.session_id == session_id)
                .order_by(desc(ConversationRecord.timestamp))
            )

            if limit is not None:
                stmt = stmt.limit(limit)

            records = session.exec(stmt).all()
            return list(records)

    # TEST-ONLY METHODS
    async def clear_session(self, session_id: str) -> int:
        """
        Clear all conversation records for a session.

        **TEST-ONLY METHOD** - Used exclusively by tests for cleanup.
        """
        with Session(self.engine) as session:
            stmt = select(ConversationRecord).where(
                ConversationRecord.session_id == session_id
            )
            records = session.exec(stmt).all()

            for record in records:
                session.delete(record)

            session.commit()
            return len(records)

    def get_stats(self) -> dict[str, int | str]:
        """
        Get statistics about the database storage.

        **TEST-ONLY METHOD** - Used exclusively by tests for verification.
        """
        with Session(self.engine) as session:
            # Count total records
            total_stmt = select(ConversationRecord)
            total_records = len(session.exec(total_stmt).all())

            # Count unique sessions using SQLAlchemy
            from sqlalchemy import func

            unique_sessions_stmt = select(
                func.count(func.distinct(ConversationRecord.session_id))
            )
            unique_sessions = session.exec(unique_sessions_stmt).one() or 0

            return {
                "provider": "SQLModel SQLite",
                "total_records": total_records,
                "unique_sessions": unique_sessions,
                "max_context_records": self._max_context_records,
                "retention_days": self._retention_days,
            }

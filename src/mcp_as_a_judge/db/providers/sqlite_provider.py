"""
SQLModel-based SQLite database provider for conversation history.

This provider uses SQLModel with SQLAlchemy for type-safe database operations.
It supports both in-memory (:memory:) and file-based SQLite storage.
"""

import uuid
import time

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, asc, desc, select

from mcp_as_a_judge.db.cleanup_service import ConversationCleanupService
from mcp_as_a_judge.db.interface import ConversationHistoryDB, ConversationRecord
from mcp_as_a_judge.logging_config import get_logger

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

    def __init__(self, max_session_records: int = 20, url: str = "") -> None:
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

        self._max_session_records = max_session_records

        # Initialize cleanup service for time-based cleanup
        self._cleanup_service = ConversationCleanupService(engine=self.engine)

        # Create tables
        self._create_tables()

        logger.info(
            f"🗄️ SQLModel SQLite provider initialized: {connection_string}, "
            f"max_records={max_session_records}, retention_days={self._cleanup_service.retention_days}"
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
        Remove records older than retention_days using the cleanup service.
        This runs once per day to avoid excessive cleanup operations.
        """
        return self._cleanup_service.cleanup_old_records()

    def _cleanup_old_messages(self, session_id: str) -> int:
        """
        Remove old messages from a session using FIFO strategy.
        Keeps only the most recent max_session_records messages per session.
        """
        with Session(self.engine) as session:
            # Count current messages in session
            count_stmt = select(ConversationRecord).where(
                ConversationRecord.session_id == session_id
            )
            current_records = session.exec(count_stmt).all()
            current_count = len(current_records)

            logger.info(
                f"🧹 FIFO cleanup check for session {session_id}: {current_count} records "
                f"(max: {self._max_session_records})"
            )

            if current_count <= self._max_session_records:
                logger.info("   No cleanup needed - within limits")
                return 0

            # Get oldest records to remove (FIFO)
            records_to_remove = current_count - self._max_session_records
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
        timestamp = int(time.time())

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

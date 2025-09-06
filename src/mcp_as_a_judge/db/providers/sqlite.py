"""
In-memory database provider for conversation history.

This provider uses SQLite in-memory database (:memory:) for storing conversation history.
It provides SQL query capabilities while keeping data in memory only.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timedelta

from ..interface import ConversationHistoryDB, ConversationRecord

# Set up logger
logger = logging.getLogger(__name__)


class SQLiteProvider(ConversationHistoryDB):
    """
    SQLite database provider for conversation history.

    Supports both in-memory (:memory:) and file-based SQLite storage
    depending on the URL configuration.

    Features:
    - In-memory or file-based SQLite storage
    - LRU cleanup per session
    - Time-based cleanup (configurable retention)
    - Session-based conversation retrieval
    """

    def __init__(self, max_context_records: int = 20, retention_days: int = 1, url: str = "") -> None:
        """Initialize the SQLite database with LRU and time-based cleanup."""
        # Parse URL to get SQLite connection string
        connection_string = self._parse_sqlite_url(url)

        self._conn = sqlite3.connect(connection_string)
        self._conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        self._max_context_records = max_context_records
        self._retention_days = retention_days
        self._last_cleanup_time = datetime.utcnow()
        self._create_tables()

    def _parse_sqlite_url(self, url: str) -> str:
        """
        Parse SQLite URL to get connection string in memory or file format.

        Args:
            url: Database URL from config

        Returns:
            SQLite connection string

        Examples:
            "" -> ":memory:"
            "sqlite://:memory:" -> ":memory:"
            "sqlite:///path/to/file.db" -> "/path/to/file.db"
            ":memory:" -> ":memory:"
        """
        if not url or url.strip() == "":
            return ":memory:"

        url = url.strip()

        # Handle direct :memory: specification
        if url == ":memory:":
            return ":memory:"

        # Handle sqlite://:memory: format
        if url == "sqlite://:memory:":
            return ":memory:"

        # Handle sqlite:///path/to/file.db format (absolute path)
        if url.startswith("sqlite:///"):
            return url[9:]  # Remove "sqlite://" prefix, keep leading /

        # Handle sqlite://path/to/file.db format (relative path)
        if url.startswith("sqlite://"):
            return url[9:]  # Remove "sqlite://" prefix

        # Default to in-memory for unknown formats
        logger.warning(f"Unknown SQLite URL format: {url}, defaulting to :memory:")
        return ":memory:"

    def _create_tables(self) -> None:
        """Create the conversation_history table."""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                source TEXT NOT NULL,
                input TEXT NOT NULL,  -- JSON array as string
                output TEXT NOT NULL,
                timestamp TEXT NOT NULL  -- ISO format datetime
            )
        """)

        # Create index for faster session queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_timestamp
            ON conversation_history(session_id, timestamp DESC)
        """)

        self._conn.commit()

    def _should_run_cleanup(self) -> bool:
        """
        Determine if cleanup should run based on daily schedule.

        Returns:
            True if cleanup should run
        """
        now = datetime.utcnow()
        time_since_last_cleanup = now - self._last_cleanup_time

        # Run cleanup once per day (24 hours)
        return time_since_last_cleanup > timedelta(days=1)

    def _cleanup_old_records(self) -> int:
        """
        Remove records older than retention_days across all sessions.
        Only runs when _should_run_cleanup() returns True.

        Returns:
            Number of records removed
        """
        if not self._should_run_cleanup():
            return 0

        cursor = self._conn.cursor()

        # Calculate cutoff timestamp (retention_days ago)
        cutoff_time = datetime.utcnow() - timedelta(days=self._retention_days)
        cutoff_iso = cutoff_time.isoformat()

        # Count records to be deleted
        cursor.execute("""
            SELECT COUNT(*) as count FROM conversation_history
            WHERE timestamp < ?
        """, (cutoff_iso,))

        old_count = cursor.fetchone()['count']

        if old_count == 0:
            logger.info(f"🧹 Daily cleanup: No records older than {self._retention_days} days")
            self._last_cleanup_time = datetime.utcnow()
            return 0

        # Delete old records
        cursor.execute("""
            DELETE FROM conversation_history
            WHERE timestamp < ?
        """, (cutoff_iso,))

        deleted_count = cursor.rowcount
        self._conn.commit()

        # Reset cleanup tracking
        self._last_cleanup_time = datetime.utcnow()

        logger.info(f"🧹 Daily cleanup: Deleted {deleted_count} records older than {self._retention_days} days")
        return deleted_count

    def _cleanup_old_messages(self, session_id: str) -> int:
        """
        Remove old messages from a session using LRU (Least Recently Used) strategy.
        Keeps only the most recent max_context_records messages per session.

        Args:
            session_id: Session to cleanup

        Returns:
            Number of messages removed
        """

        cursor = self._conn.cursor()

        # Count current messages in session
        cursor.execute("""
            SELECT COUNT(*) as count FROM conversation_history
            WHERE session_id = ?
        """, (session_id,))

        current_count = cursor.fetchone()['count']

        logger.info(f"🧹 LRU cleanup check for session {session_id}: {current_count} records (max: {self._max_context_records})")

        if current_count <= self._max_context_records:
            logger.info("   No cleanup needed - within limits")
            return 0

        # Calculate how many messages to remove (LRU cleanup)
        messages_to_remove = current_count - self._max_context_records
        logger.info(f"   Need to remove {messages_to_remove} oldest records")

        # Get the oldest message IDs to remove (LRU - remove least recently used)
        cursor.execute("""
            SELECT id, source, timestamp FROM conversation_history
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, messages_to_remove))

        old_records = cursor.fetchall()
        old_message_ids = [row['id'] for row in old_records]

        # Log what's being removed
        logger.info(f"🗑️ Removing {len(old_message_ids)} oldest records:")
        for i, record in enumerate(old_records, 1):
            logger.info(f"   {i}. ID: {record['id'][:8]}... | Source: {record['source']} | Timestamp: {record['timestamp']}")

        # Remove the old messages
        if old_message_ids:
            placeholders = ','.join('?' * len(old_message_ids))
            # Safe: placeholders contains only '?' characters, no user data
            query = f"""
                DELETE FROM conversation_history
                WHERE id IN ({placeholders})
            """  # noqa: S608
            cursor.execute(query, tuple(old_message_ids))

            removed_count = cursor.rowcount
            self._conn.commit()

            logger.info(f"✅ LRU cleanup completed: removed {removed_count} records from session {session_id}")
            return removed_count

        return 0

    def __del__(self) -> None:
        """Close the database connection when the object is destroyed."""
        if hasattr(self, '_conn'):
            self._conn.close()

    async def save_conversation(
        self,
        session_id: str,
        source: str,
        input_data: str,
        output: str
    ) -> str:
        """Save a conversation record to SQLite in-memory database with LRU cleanup."""
        record_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        logger.info(f"💾 Saving conversation to SQLite DB: record {record_id} for session {session_id}, source {source} at {timestamp}")


        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO conversation_history
            (id, session_id, source, input, output, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (record_id, session_id, source, input_data, output, timestamp))

        self._conn.commit()
        logger.info("✅ Successfully inserted record into conversation_history table")

        # Daily cleanup: run once per day to remove old records
        self._cleanup_old_records()

        # Always perform LRU cleanup for this session (lightweight)
        self._cleanup_old_messages(session_id)

        return record_id



    async def get_session_conversations(
        self,
        session_id: str,
        limit: int | None = None
    ) -> list[ConversationRecord]:
        """Retrieve all conversation records for a session."""
        cursor = self._conn.cursor()

        if limit is not None:
            cursor.execute("""
                SELECT id, session_id, source, input, output, timestamp
                FROM conversation_history
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
        else:
            cursor.execute("""
                SELECT id, session_id, source, input, output, timestamp
                FROM conversation_history
                WHERE session_id = ?
                ORDER BY timestamp DESC
            """, (session_id,))

        rows = cursor.fetchall()
        records = []

        for row in rows:
            records.append(ConversationRecord(
                id=row['id'],
                session_id=row['session_id'],
                source=row['source'],
                input=row['input'],
                output=row['output'],
                timestamp=datetime.fromisoformat(row['timestamp'])
            ))

        return records

    # TEST-ONLY METHODS
    async def clear_session(self, session_id: str) -> int:
        """
        Clear all conversation records for a session.

        **TEST-ONLY METHOD** - Used exclusively by tests for cleanup.
        """
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))

        deleted_count = cursor.rowcount
        self._conn.commit()
        return deleted_count

    def get_stats(self) -> dict[str, int | str]:
        """
        Get statistics about the SQLite storage.

        **TEST-ONLY METHOD** - Used exclusively by tests for verification.
        """
        cursor = self._conn.cursor()

        # Get total records
        cursor.execute("SELECT COUNT(*) as count FROM conversation_history")
        total_records = cursor.fetchone()['count']

        # Get total sessions
        cursor.execute("SELECT COUNT(DISTINCT session_id) as count FROM conversation_history")
        total_sessions = cursor.fetchone()['count']

        return {
            "total_records": total_records,
            "total_sessions": total_sessions,
            "database_type": "sqlite"
        }

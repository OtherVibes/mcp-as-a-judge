"""
In-memory database provider for conversation history.

This provider uses SQLite in-memory database (:memory:) for storing conversation history.
It provides SQL query capabilities while keeping data in memory only.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from ..interface import ConversationHistoryDB, ConversationRecord


class InMemoryProvider(ConversationHistoryDB):
    """SQLite in-memory implementation of ConversationHistoryDB."""

    def __init__(self, max_context_records: int = 20) -> None:
        """Initialize the SQLite in-memory database with LRU cleanup."""
        self._conn = sqlite3.connect(':memory:')
        self._conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        self._max_context_records = max_context_records
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the conversation_history table."""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                source TEXT NOT NULL,
                input TEXT NOT NULL,
                context TEXT NOT NULL,  -- JSON array as string
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

        if current_count <= self._max_context_records:
            return 0

        # Calculate how many messages to remove (LRU cleanup)
        messages_to_remove = current_count - self._max_context_records

        # Get the oldest message IDs to remove (LRU - remove least recently used)
        cursor.execute("""
            SELECT id FROM conversation_history
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, messages_to_remove))

        old_message_ids = [row['id'] for row in cursor.fetchall()]

        # Remove the old messages
        if old_message_ids:
            placeholders = ','.join('?' * len(old_message_ids))
            cursor.execute(f"""
                DELETE FROM conversation_history
                WHERE id IN ({placeholders})
            """, old_message_ids)

            removed_count = cursor.rowcount
            self._conn.commit()
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
        context: List[str],
        output: str
    ) -> str:
        """Save a conversation record to SQLite in-memory database with LRU cleanup."""
        record_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        context_json = json.dumps(context)

        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO conversation_history
            (id, session_id, source, input, context, output, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (record_id, session_id, source, input_data, context_json, output, timestamp))

        self._conn.commit()

        # Perform LRU cleanup after saving (remove oldest messages if limit exceeded)
        removed_count = self._cleanup_old_messages(session_id)
        if removed_count > 0:
            print(f"LRU cleanup: Removed {removed_count} old messages from session {session_id}")

        return record_id
    
    async def get_conversation(self, record_id: str) -> Optional[ConversationRecord]:
        """Retrieve a conversation record by ID."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT id, session_id, source, input, context, output, timestamp
            FROM conversation_history
            WHERE id = ?
        """, (record_id,))

        row = cursor.fetchone()
        if row is None:
            return None

        return ConversationRecord(
            id=row['id'],
            session_id=row['session_id'],
            source=row['source'],
            input=row['input'],
            context=json.loads(row['context']),
            output=row['output'],
            timestamp=datetime.fromisoformat(row['timestamp'])
        )
    
    async def get_session_conversations(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationRecord]:
        """Retrieve all conversation records for a session."""
        cursor = self._conn.cursor()

        if limit is not None:
            cursor.execute("""
                SELECT id, session_id, source, input, context, output, timestamp
                FROM conversation_history
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
        else:
            cursor.execute("""
                SELECT id, session_id, source, input, context, output, timestamp
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
                context=json.loads(row['context']),
                output=row['output'],
                timestamp=datetime.fromisoformat(row['timestamp'])
            ))

        return records
    
    async def get_recent_conversations(
        self,
        session_id: str,
        count: int = 10
    ) -> List[str]:
        """Get the most recent conversation IDs for context building."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT id
            FROM conversation_history
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, count))

        rows = cursor.fetchall()
        return [row['id'] for row in rows]
    
    async def delete_conversation(self, record_id: str) -> bool:
        """Delete a conversation record."""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM conversation_history WHERE id = ?", (record_id,))

        deleted = cursor.rowcount > 0
        self._conn.commit()
        return deleted
    
    async def clear_session(self, session_id: str) -> int:
        """Clear all conversation records for a session."""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))

        deleted_count = cursor.rowcount
        self._conn.commit()
        return deleted_count

    def get_stats(self) -> dict[str, int]:
        """Get statistics about the SQLite in-memory storage (for debugging/monitoring)."""
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
            "database_type": "sqlite_memory"
        }
    
    def get_stats(self) -> dict[str, int]:
        """Get statistics about the SQLite in-memory storage (for debugging/monitoring)."""
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
            "database_type": "sqlite_memory"
        }

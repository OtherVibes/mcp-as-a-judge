"""
Database cleanup service for conversation history records.

This service handles time-based cleanup operations for conversation history records,
removing records older than the retention period (default: 1 day).
"""

from datetime import datetime, timedelta, UTC

from sqlalchemy import Engine, func
from sqlmodel import Session, select

from mcp_as_a_judge.constants import MAX_TOTAL_SESSIONS, RECORD_RETENTION_DAYS
from mcp_as_a_judge.db.interface import ConversationRecord
from mcp_as_a_judge.logging_config import get_logger

# Set up logger
logger = get_logger(__name__)


class ConversationCleanupService:
    """
    Service for cleaning up old conversation history records.

    Implements session-based LRU cleanup strategy:
    - Maintains max 2000 sessions by removing least recently used sessions
    - Runs once per day to avoid performance overhead

    LRU vs FIFO for Better User Experience:
    - LRU (Least Recently Used): Keeps sessions that users are actively using,
      even if they're old
    - FIFO (First In, First Out): Would remove oldest sessions regardless of
      recent activity
    - LRU provides better UX because active conversations are preserved longer

    Note: Per-session FIFO cleanup (max 20 records) is handled by the SQLite provider.
    """

    def __init__(self, engine: Engine) -> None:
        """
        Initialize the cleanup service.

        Args:
            engine: SQLAlchemy engine for database operations
        """
        self.engine = engine
        self.max_total_sessions = MAX_TOTAL_SESSIONS
        self.retention_days = RECORD_RETENTION_DAYS
        self.last_cleanup_time = datetime.now(UTC)
        self.last_session_cleanup_time = datetime.now(UTC)

    def cleanup_old_records(self) -> int:
        """
        Remove records older than retention_days.
        This runs once per day to avoid excessive cleanup operations.

        Returns:
            Number of records deleted
        """
        # Only run cleanup once per day
        if (datetime.now(UTC) - self.last_cleanup_time).days < 1:
            return 0

        cutoff_date = datetime.now(UTC) - timedelta(days=self.retention_days)

        with Session(self.engine) as session:
            # Count old records
            old_count_stmt = select(ConversationRecord).where(
                ConversationRecord.timestamp < cutoff_date
            )
            old_records = session.exec(old_count_stmt).all()
            old_count = len(old_records)

            if old_count == 0:
                logger.info(
                    f"🧹 Daily cleanup: No records older than {self.retention_days} days"
                )
                self.last_cleanup_time = datetime.now(UTC)
                return 0

            # Delete old records
            for record in old_records:
                session.delete(record)

            session.commit()

            # Reset cleanup tracking
            self.last_cleanup_time = datetime.now(UTC)

            logger.info(
                f"🧹 Daily cleanup: Deleted {old_count} records older than "
                f"{self.retention_days} days"
            )
            return old_count

    def get_session_count(self) -> int:
        """
        Get the total number of unique sessions in the database.

        Returns:
            Number of unique sessions
        """
        with Session(self.engine) as session:
            # Count distinct session_ids
            count_stmt = select(
                func.count(func.distinct(ConversationRecord.session_id))
            )
            result = session.exec(count_stmt).first()
            return result or 0

    def get_least_recently_used_sessions(self, limit: int) -> list[str]:
        """
        Get session IDs of the least recently used sessions.

        Uses LRU strategy: finds sessions with the oldest "last activity" timestamp.
        Last activity = MAX(timestamp) for each session (most recent record in session).

        Args:
            limit: Number of session IDs to return

        Returns:
            List of session IDs ordered by last activity (oldest first)
        """
        with Session(self.engine) as session:
            # Find sessions with oldest last activity (LRU)
            # GROUP BY session_id, ORDER BY MAX(timestamp) ASC to get least recently used
            lru_stmt = (
                select(
                    ConversationRecord.session_id,
                    func.max(ConversationRecord.timestamp).label("last_activity"),
                )
                .group_by(ConversationRecord.session_id)
                .order_by(func.max(ConversationRecord.timestamp).asc())
                .limit(limit)
            )

            results = session.exec(lru_stmt).all()
            return [result.session_id for result in results]

    def delete_sessions(self, session_ids: list[str]) -> int:
        """
        Bulk delete all records for the given session IDs.

        Args:
            session_ids: List of session IDs to delete

        Returns:
            Number of records deleted
        """
        if not session_ids:
            return 0

        with Session(self.engine) as session:
            # Count records before deletion for logging
            count_stmt = select(ConversationRecord).where(
                ConversationRecord.session_id.in_(session_ids)
            )
            records_to_delete = session.exec(count_stmt).all()
            delete_count = len(records_to_delete)

            # Bulk delete all records for these sessions
            for record in records_to_delete:
                session.delete(record)

            session.commit()

            logger.info(
                f"🗑️ Deleted {delete_count} records from {len(session_ids)} sessions: "
                f"{', '.join(session_ids[:3])}{'...' if len(session_ids) > 3 else ''}"
            )

            return delete_count

    def cleanup_excess_sessions(self) -> int:
        """
        Remove least recently used sessions when total sessions exceed
        MAX_TOTAL_SESSIONS.

        This implements LRU (Least Recently Used) cleanup strategy:
        - Keeps sessions that users are actively using (better UX than FIFO)
        - Only runs once per day to avoid excessive cleanup operations
        - During the day, session count can exceed limit
          (e.g., 5000 sessions is not a memory issue)
        - Daily cleanup brings it back to the target limit (2000 sessions)
        - Removes entire sessions (all records for those session_ids)

        Returns:
            Number of records deleted
        """
        # Only run session cleanup once per day
        if (datetime.now(UTC) - self.last_session_cleanup_time).days < 1:
            return 0

        current_session_count = self.get_session_count()

        if current_session_count <= self.max_total_sessions:
            logger.info(
                f"🧹 Daily session LRU cleanup: {current_session_count} sessions "
                f"(max: {self.max_total_sessions}) - no cleanup needed"
            )
            self.last_session_cleanup_time = datetime.now(UTC)
            return 0

        # Calculate how many sessions to remove
        sessions_to_remove = current_session_count - self.max_total_sessions

        logger.info(
            f"🧹 Daily session LRU cleanup: {current_session_count} sessions exceeds limit "
            f"({self.max_total_sessions}), removing {sessions_to_remove} "
            f"least recently used sessions"
        )

        # Get least recently used sessions
        lru_session_ids = self.get_least_recently_used_sessions(sessions_to_remove)

        if not lru_session_ids:
            logger.warning("🧹 No sessions found for LRU cleanup")
            self.last_session_cleanup_time = datetime.now(UTC)
            return 0

        # Delete all records for these sessions
        deleted_count = self.delete_sessions(lru_session_ids)

        # Reset cleanup tracking
        self.last_session_cleanup_time = datetime.now(UTC)

        logger.info(
            f"✅ Daily session LRU cleanup completed: removed {sessions_to_remove} sessions, "
            f"deleted {deleted_count} records"
        )

        return deleted_count

"""
Database cleanup service for conversation history records.

This service handles time-based cleanup operations for conversation history records,
removing records older than the retention period (default: 1 day).
"""

from datetime import datetime, timedelta

from sqlalchemy import Engine
from sqlmodel import Session, select

from mcp_as_a_judge.constants import RECORD_RETENTION_DAYS
from mcp_as_a_judge.db.interface import ConversationRecord
from mcp_as_a_judge.logging_config import get_logger

# Set up logger
logger = get_logger(__name__)


class ConversationCleanupService:
    """
    Service for cleaning up old conversation history records.

    Handles time-based cleanup: Removes records older than retention period.
    Note: LRU cleanup is handled by the SQLite provider during save operations.
    """

    def __init__(self, engine: Engine) -> None:
        """
        Initialize the cleanup service.

        Args:
            engine: SQLAlchemy engine for database operations
        """
        self.engine = engine
        self.retention_days = RECORD_RETENTION_DAYS
        self.last_cleanup_time = datetime.utcnow()

    def cleanup_old_records(self) -> int:
        """
        Remove records older than retention_days.
        This runs once per day to avoid excessive cleanup operations.

        Returns:
            Number of records deleted
        """
        # Only run cleanup once per day
        if (datetime.utcnow() - self.last_cleanup_time).days < 1:
            return 0

        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

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
                self.last_cleanup_time = datetime.utcnow()
                return 0

            # Delete old records
            for record in old_records:
                session.delete(record)

            session.commit()

            # Reset cleanup tracking
            self.last_cleanup_time = datetime.utcnow()

            logger.info(
                f"🧹 Daily cleanup: Deleted {old_count} records older than {self.retention_days} days"
            )
            return old_count

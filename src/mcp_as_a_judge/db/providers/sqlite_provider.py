"""
SQLModel-based SQLite database provider for conversation history.

This provider uses SQLModel with SQLAlchemy for type-safe database operations.
It supports both in-memory (:memory:) and file-based SQLite storage.
"""

import time
import uuid

from sqlalchemy import create_engine, delete, func
from sqlmodel import Session, SQLModel, asc, desc, select

from mcp_as_a_judge.core.constants import MAX_CONTEXT_TOKENS
from mcp_as_a_judge.core.logging_config import get_logger
from mcp_as_a_judge.db.cleanup_service import ConversationCleanupService
from mcp_as_a_judge.db.interface import ConversationHistoryDB, ConversationRecord
from mcp_as_a_judge.db.token_utils import calculate_tokens_in_record, detect_model_name

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
    - Two-level cleanup strategy:
      1. Session-based LRU cleanup (runs when new sessions are created,
         removes least recently used)
      2. Per-session hybrid cleanup (respects both record count and token limits, runs on every save)
    - Token-aware storage and retrieval
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

        # Initialize cleanup service for LRU session cleanup
        self._cleanup_service = ConversationCleanupService(engine=self.engine)

        # Create tables
        self._create_tables()

        logger.info(
            f"SQLModel SQLite provider initialized: {connection_string}, "
            f"max_records_per_session={max_session_records}, "
            f"max_total_sessions={self._cleanup_service.max_total_sessions}"
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
        logger.info("Created conversation_history table with SQLModel")

    def _cleanup_excess_sessions(self) -> int:
        """
        Remove least recently used sessions when total sessions exceed limit.
        This implements LRU cleanup to maintain session limit for better memory
        management.
        Runs immediately when new sessions are created and limit is exceeded.
        """
        return self._cleanup_service.cleanup_excess_sessions()

    async def _cleanup_old_messages(self, session_id: str) -> int:
        """
        Remove old messages from a session using token-based FIFO cleanup.

        Uses dynamic token limits based on current model (get_llm_input_limit).
        Removes oldest records until total tokens are within the model's input limit.

        Optimization: Single DB query with ORDER BY, then in-memory list operations.
        """
        with Session(self.engine) as session:
            # Get current records ordered by timestamp DESC (newest first for token calculation)
            count_stmt = (
                select(ConversationRecord)
                .where(ConversationRecord.session_id == session_id)
                .order_by(
                    desc(ConversationRecord.timestamp),
                    desc(ConversationRecord.id),
                )
            )
            current_records = list(session.exec(count_stmt).all())
            current_count = len(current_records)

            logger.info(
                f"Cleanup check for session {session_id}: {current_count} records "
                f"(max: {self._max_session_records})"
            )

            removed_count = 0

            # STEP 1: Handle record count limit
            while len(current_records) > self._max_session_records:
                logger.info("   📊 Record limit exceeded, removing oldest record")
                # Deterministically fetch oldest by ascending timestamp then id
                oldest_stmt = (
                    select(ConversationRecord)
                    .where(ConversationRecord.session_id == session_id)
                    .order_by(
                        asc(ConversationRecord.timestamp), asc(ConversationRecord.id)
                    )
                    .limit(1)
                )
                oldest_record = session.exec(oldest_stmt).first()
                if not oldest_record:
                    break
                logger.info(
                    f"   🗑️ Removing oldest record: {oldest_record.source} | {getattr(oldest_record, 'tokens', 0)} tokens | {oldest_record.timestamp}"
                )
                session.delete(oldest_record)
                removed_count += 1
                session.commit()
                # Update in-memory list
                current_records = [
                    r for r in current_records if r.id != oldest_record.id
                ]

            # STEP 2: Handle token limit using dynamic model-specific limits
            current_tokens = sum(record.tokens for record in current_records)

            # Use configured MAX_CONTEXT_TOKENS for persistent storage limits
            model_name = await detect_model_name()
            max_input_tokens = MAX_CONTEXT_TOKENS

            logger.info(
                f"   {len(current_records)} records, {current_tokens} tokens "
                f"(max: {max_input_tokens} for model: {model_name or 'default'})"
            )

            if current_tokens > max_input_tokens:
                logger.info(
                    f"   🚨 Token limit exceeded, removing oldest records to fit within {max_input_tokens} tokens"
                )

                # Calculate which records to keep (newest first, within token limit)
                records_to_keep = []
                running_tokens = 0

                for record in current_records:  # Already ordered newest first
                    if running_tokens + record.tokens <= max_input_tokens:
                        records_to_keep.append(record)
                        running_tokens += record.tokens
                    else:
                        break

                # Remove records that didn't make the cut
                records_to_remove_for_tokens = current_records[len(records_to_keep) :]

                if records_to_remove_for_tokens:
                    logger.info(
                        f"   🗑️ Removing {len(records_to_remove_for_tokens)} records for token limit "
                        f"(keeping {len(records_to_keep)} records, {running_tokens} tokens)"
                    )

                    for record in records_to_remove_for_tokens:
                        logger.info(
                            f"      - {record.source} | {record.tokens} tokens | {record.timestamp}"
                        )
                        session.delete(record)
                        removed_count += 1

                    session.commit()
                    logger.info(
                        f"   ✅ Removed {len(records_to_remove_for_tokens)} additional records due to token limit"
                    )

            if removed_count > 0:
                logger.info(
                    f"✅ Cleanup completed for session {session_id}: removed {removed_count} total records"
                )
            else:
                logger.info("   ✅ No cleanup needed - within both limits")

            return removed_count

    def _is_new_session(self, session_id: str) -> bool:
        """Check if this is a new session (no existing records)."""
        with Session(self.engine) as session:
            existing_record = session.exec(
                select(ConversationRecord)
                .where(ConversationRecord.session_id == session_id)
                .limit(1)
            ).first()
            return existing_record is None

    async def save_conversation(
        self, session_id: str, source: str, input_data: str, output: str
    ) -> str:
        """Save a conversation record to SQLite database with LRU cleanup."""
        record_id = str(uuid.uuid4())
        # Nanosecond precision to avoid ties under rapid inserts
        try:
            timestamp = int(time.time_ns())
        except AttributeError:
            # Fallback for very old Python versions
            timestamp = int(time.time() * 1_000_000_000)

        logger.info(
            f"Saving conversation to SQLModel SQLite DB: record {record_id} "
            f"for session {session_id}, source {source} at {timestamp}"
        )

        # Check if this is a new session before saving
        is_new_session = self._is_new_session(session_id)

        # Calculate token count for input + output
        token_count = await calculate_tokens_in_record(input_data, output)

        # Create new record
        record = ConversationRecord(
            id=record_id,
            session_id=session_id,
            source=source,
            input=input_data,
            output=output,
            tokens=token_count,
            timestamp=timestamp,
        )

        with Session(self.engine) as session:
            session.add(record)
            session.commit()

        logger.info("Successfully inserted record into conversation_history table")

        # Session LRU cleanup: only run when a new session is created
        if is_new_session:
            logger.info(f"🆕 New session detected: {session_id}, running LRU cleanup")
            self._cleanup_excess_sessions()

        # Per-session FIFO cleanup: maintain max records per session and model-specific token limits
        # (runs on every save)
        await self._cleanup_old_messages(session_id)

        return record_id

    async def get_session_conversations(
        self, session_id: str, limit: int | None = None
    ) -> list[ConversationRecord]:
        """Retrieve all conversation records for a session."""
        with Session(self.engine) as session:
            stmt = (
                select(ConversationRecord)
                .where(ConversationRecord.session_id == session_id)
                .order_by(
                    desc(ConversationRecord.timestamp),
                    desc(ConversationRecord.id),
                )
            )

            if limit is not None:
                stmt = stmt.limit(limit)

            records = session.exec(stmt).all()
            return list(records)

    async def get_recent_sessions(self, limit: int = 10) -> list[tuple[str, int]]:
        """Retrieve most recently active sessions with last activity timestamp."""
        with Session(self.engine) as session:
            stmt = (
                select(
                    ConversationRecord.session_id,
                    func.max(ConversationRecord.timestamp).label("last_activity"),
                )
                .group_by(ConversationRecord.session_id)
                .order_by(func.max(ConversationRecord.timestamp).desc())
                .limit(limit)
            )
            results = session.exec(stmt).all()
            # results are tuples (session_id, last_activity)
            return [(row[0], int(row[1])) for row in results]

    async def delete_previous_plan(self, session_id: str) -> None:
        """
        Delete all previous judge_coding_plan records except the most recent one.

        Uses SQL ORM to find all judge_coding_plan records for the session,
        keeps only the most recent one, and deletes the rest.
        """
        try:
            with Session(self.engine) as session:
                # Find all judge_coding_plan records for this session, ordered by timestamp DESC
                stmt = (
                    select(ConversationRecord)
                    .where(ConversationRecord.session_id == session_id)
                    .where(ConversationRecord.source == "judge_coding_plan")
                    .order_by(
                        desc(ConversationRecord.timestamp),
                        desc(ConversationRecord.id),
                    )
                )
                plan_records = list(session.exec(stmt).all())

                if len(plan_records) <= 1:
                    # No previous plans to delete
                    logger.info(
                        f"No previous judge_coding_plan records to delete for session {session_id}"
                    )
                    return

                # Keep the first record (most recent), delete the rest
                records_to_delete = plan_records[1:]  # Skip the first (most recent)
                record_ids_to_delete: list[str] = [
                    record.id for record in records_to_delete if record.id is not None
                ]

                if not record_ids_to_delete:
                    logger.info(
                        f"No valid record IDs to delete for session {session_id}"
                    )
                    return

                # Delete records using SQL IN clause with underlying SQLAlchemy session
                # Use the table name from ConversationRecord to avoid type issues
                table_name = ConversationRecord.__tablename__
                table = SQLModel.metadata.tables[table_name]
                delete_stmt = delete(table).where(table.c.id.in_(record_ids_to_delete))
                # Use the underlying SQLAlchemy session for delete operations
                session.execute(delete_stmt)
                session.commit()

                logger.info(
                    f"Successfully deleted {len(records_to_delete)} previous judge_coding_plan records for session {session_id}"
                )

        except Exception as e:
            logger.error(
                f"Error deleting previous judge_coding_plan records for session {session_id}: {e}"
            )

"""
Conversation History Service for MCP Judge Tools.

This service handles:
1. Loading historical context for LLM enrichment
2. Saving tool interactions as conversation records
3. Managing session-based conversation history
"""

from typing import Any

from mcp_as_a_judge.core.logging_config import get_logger
from mcp_as_a_judge.core.task_state import TaskState
from mcp_as_a_judge.db.db_config import Config
from mcp_as_a_judge.db.factory import create_database_provider
from mcp_as_a_judge.db.interface import ConversationHistoryDB, ConversationRecord
from mcp_as_a_judge.db.token_utils import (
    filter_records_by_token_limit,
)

# Set up logger
logger = get_logger(__name__)


class ConversationHistoryService:
    """Service for managing conversation history in judge tools."""

    def __init__(
        self, config: Config, db_provider: ConversationHistoryDB | None = None
    ):
        """
        Initialize the conversation history service.

        Args:
            config: Application configuration
            db_provider: Optional database provider (will create one if not provided)
        """
        self.config = config
        self.db = db_provider or create_database_provider(config)

    async def load_filtered_context_for_enrichment(
        self, session_id: str, current_prompt: str = "", ctx: Any = None
    ) -> list[ConversationRecord]:
        """
        Load recent conversation records for LLM context enrichment.

        Two-level filtering approach:
        1. Database already enforces storage limits (record count + token limits)
        2. Load-time filtering ensures history + current prompt fits within LLM context limits

        Args:
            session_id: Session identifier
            current_prompt: Current prompt that will be sent to LLM (for token calculation)
            ctx: MCP context for model detection and accurate token counting (optional)

        Returns:
            List of conversation records for LLM context (filtered for LLM limits)
        """
        logger.info(f"Loading conversation history for session: {session_id}")

        # Load all conversations for this session - database already contains
        # records within storage limits, but we may need to filter further for LLM context
        recent_records = await self.db.get_session_conversations(session_id)

        logger.info(f"Retrieved {len(recent_records)} conversation records from DB")

        # Apply LLM context filtering: ensure history + current prompt will fit within token limit
        # This filters the list without modifying the database (only token limit matters for LLM)
        # Pass ctx for accurate token counting when available
        filtered_records = await filter_records_by_token_limit(
            recent_records, current_prompt=current_prompt, ctx=ctx
        )

        logger.info(
            f"Returning {len(filtered_records)} conversation records for LLM context"
        )
        return filtered_records

    async def save_tool_interaction_and_cleanup(
        self, session_id: str, tool_name: str, tool_input: str, tool_output: str, step: TaskState
    ) -> str:
        """
        Save a tool interaction as a conversation record and perform automatic cleanup.

        After saving, the database provider automatically performs cleanup to enforce limits:
        - Removes old records if session exceeds MAX_SESSION_RECORDS (20)
        - Removes old records if session exceeds MAX_CONTEXT_TOKENS (50,000)
        - Removes least recently used sessions if total sessions exceed MAX_TOTAL_SESSIONS (50)

        Special cleanup for PLAN_APPROVED transition:
        - When step is PLAN_APPROVED, removes all but the last PLANNING record from the session

        Args:
            session_id: Session identifier from AI agent
            tool_name: Name of the judge tool (e.g., 'judge_coding_plan')
            tool_input: Input that was passed to the tool
            tool_output: Output/result from the tool
            step: Current workflow step that generated this record

        Returns:
            ID of the created conversation record
        """
        logger.info(
            f"Saving tool interaction to SQLite DB for session: {session_id}, tool: {tool_name}, step: {step}"
        )

        record_id = await self.db.save_conversation(
            session_id=session_id,
            source=tool_name,
            input_data=tool_input,
            output=tool_output,
            step=step,
        )

        # Special cleanup: when transitioning to PLAN_APPROVED, remove all but last PLANNING record
        if step == TaskState.PLAN_APPROVED:
            await self._cleanup_planning_records(session_id)

        logger.info(f"Saved conversation record with ID: {record_id}")
        return record_id

    async def _cleanup_planning_records(self, session_id: str) -> None:
        """
        Remove all but the last PLANNING record from a session.

        This is called when transitioning to PLAN_APPROVED to clean up
        earlier planning attempts that were not approved.

        Args:
            session_id: Session identifier to clean up
        """
        logger.info(f"Cleaning up PLANNING records for session: {session_id}")

        # Get all records for this session
        all_records = await self.db.get_session_conversations(session_id)

        # Find PLANNING records (most recent first due to ordering)
        planning_records = [r for r in all_records if r.step == TaskState.PLANNING]

        if len(planning_records) <= 1:
            logger.info(f"Found {len(planning_records)} PLANNING records, no cleanup needed")
            return

        # Keep the most recent (first in list), remove the rest
        records_to_remove = planning_records[1:]  # Skip first (most recent)

        logger.info(f"Removing {len(records_to_remove)} old PLANNING records")

        # Remove old planning records in batch
        record_ids_to_remove = [record.id for record in records_to_remove]
        removed_count = await self.db.remove_conversations_batch(record_ids_to_remove)

        logger.info(f"Successfully cleaned up {removed_count} PLANNING records")

    async def get_conversation_history(
        self, session_id: str
    ) -> list[ConversationRecord]:
        """
        Get conversation history for a session to be injected into user prompts.

        Args:
            session_id: Session identifier

        Returns:
            List of conversation records for the session (most recent first)
        """
        logger.info(f"Loading conversation history for session {session_id}")

        context_records = await self.load_filtered_context_for_enrichment(session_id)

        logger.info(
            f"Retrieved {len(context_records)} conversation records for session {session_id}"
        )

        return context_records

    def format_conversation_history_as_json_array(
        self, conversation_history: list[ConversationRecord]
    ) -> list[dict]:
        """
        Convert conversation history list to JSON array for prompt injection.

        Args:
            conversation_history: List of conversation records

        Returns:
            List of dictionaries with conversation history data including timestamps
        """
        if not conversation_history:
            return []

        logger.info(
            f"Formatting {len(conversation_history)} conversation records as JSON array"
        )

        json_array = []
        for record in conversation_history:
            json_array.append(
                {
                    "source": record.source,
                    "input": record.input,
                    "output": record.output,
                    "timestamp": record.timestamp,  # Already epoch int
                }
            )

        logger.info(f"Generated JSON array with {len(json_array)} records")
        return json_array

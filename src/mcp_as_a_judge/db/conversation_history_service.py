"""
Conversation History Service for MCP Judge Tools.

This service handles:
1. Loading historical context for LLM enrichment
2. Saving tool interactions as conversation records
3. Managing session-based conversation history
"""

from mcp_as_a_judge.db import (
    ConversationHistoryDB,
    ConversationRecord,
    create_database_provider,
)
from mcp_as_a_judge.db.db_config import Config
from mcp_as_a_judge.logging_config import get_logger

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

    async def load_context_for_enrichment(
        self, session_id: str
    ) -> list[ConversationRecord]:
        """
        Load recent conversation records for LLM context enrichment.

        Args:
            session_id: Session identifier

        Returns:
            List of conversation records for LLM context
        """
        logger.info(f"🔍 Loading conversation history for session: {session_id}")

        # Load recent conversations for this session
        recent_records = await self.db.get_session_conversations(
            session_id=session_id,
            limit=self.config.database.context_enrichment_count,  # load last X records
        )

        logger.info(f"📚 Retrieved {len(recent_records)} conversation records from DB")
        return recent_records

    async def save_tool_interaction(
        self, session_id: str, tool_name: str, tool_input: str, tool_output: str
    ) -> str:
        """
        Save a tool interaction as a conversation record.

        Args:
            session_id: Session identifier from AI agent
            tool_name: Name of the judge tool (e.g., 'judge_coding_plan')
            tool_input: Input that was passed to the tool
            tool_output: Output/result from the tool

        Returns:
            ID of the created conversation record
        """
        logger.info(
            f"💾 Saving tool interaction to SQLite DB for session: {session_id}, tool: {tool_name}"
        )

        record_id = await self.db.save_conversation(
            session_id=session_id,
            source=tool_name,
            input_data=tool_input,
            output=tool_output,
        )

        logger.info(f"✅ Saved conversation record with ID: {record_id}")
        return record_id



    async def get_conversation_history(self, session_id: str) -> list[ConversationRecord]:
        """
        Get conversation history for a session to be injected into user prompts.

        Args:
            session_id: Session identifier

        Returns:
            List of conversation records for the session (most recent first)
        """
        logger.info(f"🔄 Loading conversation history for session {session_id}")

        context_records = await self.load_context_for_enrichment(session_id)

        logger.info(f"📝 Retrieved {len(context_records)} conversation records for session {session_id}")

        return context_records

    def format_conversation_history_as_context(self, conversation_history: list[ConversationRecord]) -> str:
        """
        Convert conversation history list to formatted string for context field.

        Args:
            conversation_history: List of conversation records

        Returns:
            Formatted string representation of conversation history
        """
        if not conversation_history:
            return ""

        logger.info(f"📝 Formatting {len(conversation_history)} conversation records as context string")

        context_parts = []
        for record in conversation_history:
            context_parts.append(f"Tool: {record.source}")
            context_parts.append(f"Input: {record.input}")
            context_parts.append(f"Output: {record.output}")
            context_parts.append("")  # Empty line between records

        formatted_context = "\n".join(context_parts).strip()
        logger.info(f"📝 Generated context string: {len(formatted_context)} characters")

        return formatted_context



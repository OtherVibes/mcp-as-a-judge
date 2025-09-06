"""
Conversation History Service for MCP Judge Tools.

This service handles:
1. Loading historical context for LLM enrichment
2. Saving tool interactions as conversation records
3. Managing session-based conversation history
"""

import logging

from ..config import Config
from . import ConversationHistoryDB, ConversationRecord, create_database_provider

# Set up logger
logger = logging.getLogger(__name__)


class ConversationHistoryService:
    """Service for managing conversation history in judge tools."""

    def __init__(self, config: Config, db_provider: ConversationHistoryDB | None = None):
        """
        Initialize the conversation history service.

        Args:
            config: Application configuration
            db_provider: Optional database provider (will create one if not provided)
        """
        self.config = config
        self.db = db_provider or create_database_provider(config)

    async def load_context_for_enrichment(self, session_id: str) -> list[ConversationRecord]:
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
            limit=self.config.database.context_enrichment_count # load last X records
        )

        logger.info(f"📚 Retrieved {len(recent_records)} conversation records from DB")
        return recent_records

    async def save_tool_interaction(
        self,
        session_id: str,
        tool_name: str,
        tool_input: str,
        tool_output: str
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
        logger.info(f"💾 Saving tool interaction to SQLite DB for session: {session_id}, tool: {tool_name}")

        record_id = await self.db.save_conversation(
            session_id=session_id,
            source=tool_name,
            input_data=tool_input,
            output=tool_output
        )

        logger.info(f"✅ Saved conversation record with ID: {record_id}")
        return record_id

    def format_context_for_llm(self, context_records: list[ConversationRecord]) -> str:
        """
        Format conversation history for LLM context enrichment.

        Args:
            context_records: Recent conversation records

        Returns:
            Formatted context string for LLM
        """
        if not context_records:
            logger.info("📝 No conversation history to format for LLM context")
            return "No previous conversation history available."

        logger.info(f"📝 Formatting {len(context_records)} conversation records for LLM context enrichment")

        context_lines = ["## Previous Conversation History"]
        context_lines.append("Here are the recent interactions in this session for context:")
        context_lines.append("")

        # Format records (most recent first)
        for i, record in enumerate(context_records, 1):
            context_lines.append(f"### {i}. {record.source} ({record.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
            context_lines.append(f"**Input:** {record.input}")
            context_lines.append(f"**Output:** {record.output}")
            context_lines.append("")
            logger.info(f"   Formatted record {i}: {record.source} from {record.timestamp}")

        context_lines.append("---")
        context_lines.append("Use this context to make more informed decisions.")
        context_lines.append("")

        formatted_context = "\n".join(context_lines)
        logger.info(f"📝 Generated context string: {len(formatted_context)} characters")

        return formatted_context

    ### TEST-ONLY METHODS
    async def get_session_summary(self, session_id: str) -> dict:
        """
        Get a summary of the session's conversation history.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session statistics
        """
        all_records = await self.db.get_session_conversations(session_id)

        # Count by tool type
        tool_counts: dict[str, int] = {}
        for record in all_records:
            tool_counts[record.source] = tool_counts.get(record.source, 0) + 1

        return {
            "session_id": session_id,
            "total_interactions": len(all_records),
            "tool_usage": tool_counts,
            "latest_interaction": all_records[0].timestamp.isoformat() if all_records else None,
            "context_enrichment_count": self.config.database.context_enrichment_count,
            "max_context_records": self.config.database.max_context_records
        }


# Convenience functions for easy integration with existing tools

async def enrich_with_context(
    service: ConversationHistoryService,
    session_id: str,
    base_prompt: str
) -> str:
    """
    Enrich a base prompt with conversation history context.

    Args:
        service: ConversationHistoryService instance
        session_id: Session identifier
        base_prompt: Original prompt to enrich

    Returns:
        Enriched prompt with conversation history context
    """
    logger.info(f"🔄 Starting context enrichment for session {session_id}, base_prompt: {base_prompt}")

    context_records = await service.load_context_for_enrichment(session_id)
    context_text = service.format_context_for_llm(context_records)

    enriched_prompt = f"{context_text}\n## Current Request\n{base_prompt}"

    logger.info(f"🎯 Context enrichment completed for session {session_id}, enriched_prompt: {enriched_prompt}")

    return enriched_prompt




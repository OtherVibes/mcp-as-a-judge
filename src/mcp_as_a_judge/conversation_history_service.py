"""
Conversation History Service for MCP Judge Tools.

This service handles:
1. Loading historical context for LLM enrichment
2. Saving tool interactions as conversation records
3. Managing session-based conversation history
"""

from typing import List, Optional

from .config import Config
from .db import ConversationHistoryDB, ConversationRecord, create_database_provider


class ConversationHistoryService:
    """Service for managing conversation history in judge tools."""
    
    def __init__(self, config: Config, db_provider: Optional[ConversationHistoryDB] = None):
        """
        Initialize the conversation history service.
        
        Args:
            config: Application configuration
            db_provider: Optional database provider (will create one if not provided)
        """
        self.config = config
        self.db = db_provider or create_database_provider(config)
    
    async def load_context_for_enrichment(self, session_id: str) -> tuple[List[ConversationRecord], List[str]]:
        """
        Load recent conversation records for LLM context enrichment.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (conversation_records, conversation_ids)
            - conversation_records: Full records for LLM context
            - conversation_ids: Just the IDs for saving in new record's context field
        """
        count = self.config.database.context_enrichment_count
        
        # Load recent conversations for this session
        recent_records = await self.db.get_session_conversations(
            session_id=session_id,
            limit=count
        )
        
        # Extract just the IDs for context reference
        context_ids = [record.id for record in recent_records]
        
        return recent_records, context_ids
    
    async def save_tool_interaction(
        self,
        session_id: str,
        tool_name: str,
        tool_input: str,
        tool_output: str,
        context_ids: List[str]
    ) -> str:
        """
        Save a tool interaction as a conversation record.
        
        Args:
            session_id: Session identifier from AI agent
            tool_name: Name of the judge tool (e.g., 'judge_coding_plan')
            tool_input: Input that was passed to the tool
            tool_output: Output/result from the tool
            context_ids: IDs of conversation records that were used for context enrichment
            
        Returns:
            ID of the created conversation record
        """
        record_id = await self.db.save_conversation(
            session_id=session_id,
            source=tool_name,
            input_data=tool_input,
            context=context_ids,
            output=tool_output
        )
        
        return record_id
    
    def format_context_for_llm(self, context_records: List[ConversationRecord]) -> str:
        """
        Format conversation history for LLM context enrichment.
        
        Args:
            context_records: Recent conversation records
            
        Returns:
            Formatted context string for LLM
        """
        if not context_records:
            return "No previous conversation history available."
        
        context_lines = ["## Previous Conversation History"]
        context_lines.append("Here are the recent interactions in this session for context:")
        context_lines.append("")
        
        # Format records (most recent first)
        for i, record in enumerate(context_records, 1):
            context_lines.append(f"### {i}. {record.source} ({record.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
            context_lines.append(f"**Input:** {record.input}")
            context_lines.append(f"**Output:** {record.output}")
            context_lines.append("")
        
        context_lines.append("---")
        context_lines.append("Use this context to make more informed decisions.")
        context_lines.append("")
        
        return "\n".join(context_lines)
    
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
        tool_counts = {}
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
) -> tuple[str, List[str]]:
    """
    Enrich a base prompt with conversation history context.
    
    Args:
        service: ConversationHistoryService instance
        session_id: Session identifier
        base_prompt: Original prompt to enrich
        
    Returns:
        Tuple of (enriched_prompt, context_ids)
    """
    context_records, context_ids = await service.load_context_for_enrichment(session_id)
    context_text = service.format_context_for_llm(context_records)
    
    enriched_prompt = f"{context_text}\n## Current Request\n{base_prompt}"
    
    return enriched_prompt, context_ids


async def save_tool_result(
    service: ConversationHistoryService,
    session_id: str,
    tool_name: str,
    original_input: str,
    tool_result: str,
    context_ids: List[str]
) -> str:
    """
    Save a tool's result to conversation history.
    
    Args:
        service: ConversationHistoryService instance
        session_id: Session identifier
        tool_name: Name of the tool
        original_input: Original input to the tool
        tool_result: Result from the tool
        context_ids: Context IDs that were used for enrichment
        
    Returns:
        ID of the saved conversation record
    """
    return await service.save_tool_interaction(
        session_id=session_id,
        tool_name=tool_name,
        tool_input=original_input,
        tool_output=tool_result,
        context_ids=context_ids
    )

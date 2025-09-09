"""
Shared LLM workflow navigation system for enhanced MCP as a Judge.

This module provides the core calculate_next_stage function that ALL tools
use to provide consistent, context-aware workflow navigation based on task history
and current state.
"""

import json
from typing import Any

from pydantic import BaseModel, Field

from mcp_as_a_judge.constants import MAX_TOKENS
from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.logging_config import get_logger
from mcp_as_a_judge.messaging.llm_provider import llm_provider
from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskState

# Set up logger using custom get_logger function
logger = get_logger(__name__)





class WorkflowGuidance(BaseModel):
    """
    LLM-generated workflow guidance from shared calculate_next_stage method.

    This model is returned by all tools to provide consistent next steps
    and instructions for the coding assistant.

    Compatible with the original WorkflowGuidance model from models.py.
    """
    next_tool: str | None = Field(
        description="Next tool to call, or None if workflow complete"
    )
    reasoning: str = Field(
        default="",
        description="Clear explanation of why this tool should be used next"
    )
    preparation_needed: list[str] = Field(
        default_factory=list,
        description="List of things that need to be prepared before calling the recommended tool"
    )
    guidance: str = Field(
        description="Detailed step-by-step guidance for the AI assistant"
    )

    # Backward compatibility property
    @property
    def instructions(self) -> str:
        """Backward compatibility property that maps to guidance field."""
        return self.guidance


class WorkflowGuidanceSystemVars(BaseModel):
    """Variables for workflow guidance system prompt."""

    response_schema: str = Field(
        description="JSON schema for the expected response format"
    )


class WorkflowGuidanceUserVars(BaseModel):
    """Variables for workflow guidance user prompt."""

    task_id: str = Field(description="Task ID (primary key)")
    task_title: str = Field(description="Task title")
    task_description: str = Field(description="Task description")
    user_requirements: str = Field(description="Current user requirements")
    current_state: str = Field(description="Current task state")
    state_description: str = Field(description="Description of current state")
    current_operation: str = Field(description="Current operation being performed")
    state_transitions: str = Field(description="State transition diagram")
    tool_descriptions: str = Field(description="Available tool descriptions")
    conversation_context: str = Field(description="Formatted conversation history")
    operation_context: str = Field(description="Current operation context")


async def calculate_next_stage(
    task_metadata: TaskMetadata,
    current_operation: str,
    conversation_service: ConversationHistoryService,
    ctx: Any | None = None,  # MCP Context for llm_provider
    validation_result: Any | None = None,
    completion_result: Any | None = None,
    accumulated_changes: dict | None = None,
) -> WorkflowGuidance:
    """
    SHARED METHOD used by all tools to calculate next_tool and instructions.

    Uses task_id as primary key to load conversation history and context.
    Provides consistent, context-aware workflow navigation across all tools.

    Args:
        task_metadata: Current task metadata with task_id as primary key
        current_operation: Description of current operation being performed
        conversation_service: Service for loading conversation history
        validation_result: Optional validation result from current operation
        completion_result: Optional completion result from current operation
        accumulated_changes: Optional accumulated changes data

    Returns:
        WorkflowGuidance with next_tool and instructions

    Raises:
        Exception: If LLM fails to generate valid navigation
    """
    logger.info(f"🧠 Calculating next stage for task {task_metadata.task_id}")

    try:
        # Load conversation history using task_id as primary key
        # Note: For now we'll use task_id as session_id until we update the DB schema
        conversation_history = await conversation_service.get_conversation_history(
            session_id=task_metadata.task_id
        )

        # Format conversation history for LLM context
        conversation_context = _format_conversation_for_llm(conversation_history)

        # Research requirements are determined by LLM through prompts when needed
        # For now, we'll let the calling tools handle research requirement setting
        # TODO: Add proper LLM-based research inference using create_separate_messages pattern

        # Get tool descriptions and state info for the prompt
        tool_descriptions = await _get_tool_descriptions()
        state_info = task_metadata.get_current_state_info()

        # Prepare operation context
        operation_context = []
        if validation_result:
            operation_context.append(f"- Validation Result: {validation_result}")
        if completion_result:
            operation_context.append(f"- Completion Result: {completion_result}")
        if accumulated_changes:
            operation_context.append(f"- Accumulated Changes: {len(accumulated_changes)} files modified")

        # Add file tracking information
        if task_metadata.modified_files:
            operation_context.append(f"- Modified Files ({len(task_metadata.modified_files)}): {', '.join(task_metadata.modified_files)}")

            # Check implementation progress (code review comes AFTER tests are written and passing)
            if len(task_metadata.modified_files) > 0 and task_metadata.state == TaskState.IMPLEMENTING:
                if len(task_metadata.test_files) == 0:
                    operation_context.append("- IMPLEMENTATION PROGRESS: Implementation files have been created. Continue implementing ALL code AND write tests. Ensure tests are passing before calling judge_code_change.")
                else:
                    operation_context.append("- IMPLEMENTATION + TESTS: Both implementation and test files exist. Ensure ALL tests are passing, then call judge_code_change for code review.")

        # Add testing information
        if task_metadata.test_files:
            operation_context.append(f"- Test Files ({len(task_metadata.test_files)}): {', '.join(task_metadata.test_files)}")
            test_coverage = task_metadata.get_test_coverage_summary()
            operation_context.append(f"- Test Status: {test_coverage['test_status']} (All passing: {test_coverage['all_tests_passing']})")

            # Check if testing validation is complete
            if task_metadata.state == TaskState.TESTING and test_coverage['all_tests_passing']:
                operation_context.append("- TESTING VALIDATION READY: All tests are passing. Ready for judge_testing_implementation to validate test results.")

        # Add research guidance based on requirements
        if task_metadata.research_required is True:
            research_status = "completed" if task_metadata.research_completed else "pending"
            operation_context.append(f"- RESEARCH REQUIRED (scope: {task_metadata.research_scope}, status: {research_status}): Focus on authoritative, domain-relevant sources. Rationale: {task_metadata.research_rationale}")
        elif task_metadata.research_required is False:
            operation_context.append("- RESEARCH OPTIONAL: Research is optional for this task. If provided, prioritize domain-relevant, authoritative sources.")
        else:
            operation_context.append("- RESEARCH STATUS: Research requirements not yet determined (will be inferred for new tasks).")

        operation_context_str = "\n".join(operation_context) if operation_context else "- No additional context"

        # Use existing llm_provider to get LLM guidance
        logger.info(f"📤 Sending navigation request to LLM for task {task_metadata.task_id}")

        # Use the same messaging pattern as other tools
        from mcp.types import SamplingMessage

        from mcp_as_a_judge.prompt_loader import create_separate_messages

        # Create system and user variables for the workflow guidance
        system_vars = WorkflowGuidanceSystemVars(
            response_schema=json.dumps(WorkflowGuidance.model_json_schema())
        )
        user_vars = WorkflowGuidanceUserVars(
            task_id=task_metadata.task_id,
            task_title=task_metadata.title,
            task_description=task_metadata.description,
            user_requirements=task_metadata.user_requirements,
            current_state=task_metadata.state.value,
            state_description=state_info['description'],
            current_operation=current_operation,
            state_transitions="CREATED → PLANNING → PLAN_APPROVED → IMPLEMENTING → REVIEW_READY → TESTING → COMPLETED",
            tool_descriptions=tool_descriptions,
            conversation_context=conversation_context,
            operation_context=operation_context_str,
        )

        # Create messages using the established pattern with dedicated workflow guidance prompts
        messages: list[SamplingMessage] = create_separate_messages(
            "system/workflow_guidance.md",  # Dedicated system prompt for workflow guidance
            "user/workflow_guidance.md",    # Existing user prompt for workflow guidance
            system_vars,
            user_vars,
        )

        response = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=MAX_TOKENS,  # Use standardized constant for comprehensive responses
            prefer_sampling=True,  # Factory handles all message format decisions
        )

        # Parse the JSON response using the existing DRY method
        from mcp_as_a_judge.server_helpers import extract_json_from_response

        try:
            logger.info(f"🔍 Raw LLM response length: {len(response)}")
            logger.info(f"🔍 Raw LLM response preview: {response[:300]}...")

            json_content = extract_json_from_response(response)
            logger.info(f"🔍 Extracted JSON content length: {len(json_content)}")
            logger.info(f"🔍 Extracted JSON preview: {json_content[:200]}...")

            navigation_data = json.loads(json_content)
            logger.info(f"🔍 Parsed JSON keys: {list(navigation_data.keys())}")

        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"❌ Failed to parse LLM response: {e}")
            logger.error(f"❌ Raw response: {response[:500]}...")
            raise ValueError(f"Failed to parse workflow guidance response: {e}") from e

        # Validate required fields
        required_fields = ["next_tool", "reasoning", "preparation_needed", "guidance"]
        missing_fields = [field for field in required_fields if field not in navigation_data]
        if missing_fields:
            raise ValueError(f"Missing required fields in LLM response: {missing_fields}")

        # Normalize next_tool (convert "null" string to None)
        if navigation_data["next_tool"] in ["null", "None", ""]:
            navigation_data["next_tool"] = None

        workflow_guidance = WorkflowGuidance(
            next_tool=navigation_data.get("next_tool"),
            reasoning=navigation_data.get("reasoning", ""),
            preparation_needed=navigation_data.get("preparation_needed", []),
            guidance=navigation_data.get("guidance", "")
        )

        logger.info(
            f"✅ Calculated next stage: next_tool={workflow_guidance.next_tool}, "
            f"instructions_length={len(workflow_guidance.instructions)}"
        )

        return workflow_guidance

    except Exception as e:
        logger.error(f"❌ Failed to calculate next stage for task {task_metadata.task_id}: {e}")

        # Debug: Log the actual response if available
        if 'response' in locals():
            logger.error(f"🔍 Full LLM response length: {len(response)}")
            logger.error(f"🔍 Full LLM response: {response}")

            # Check if response is truncated (doesn't end with proper JSON closing)
            if not response.strip().endswith('}'):
                logger.error("⚠️ Response appears to be truncated - doesn't end with '}'")

            # Try to see if we can extract partial JSON
            try:
                from mcp_as_a_judge.server_helpers import extract_json_from_response
                json_content = extract_json_from_response(response)
                logger.error(f"🔍 Extracted JSON: {json_content}")
            except Exception as extract_error:
                logger.error(f"🔍 JSON extraction also failed: {extract_error}")

        # Return fallback navigation
        return WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred during workflow calculation",
            preparation_needed=["Review the error and task state"],
            guidance=f"Error calculating next stage: {e!s}. Please review task manually."
        )


def _format_conversation_for_llm(conversation_history) -> str:
    """
    Format conversation history for LLM context.

    Args:
        conversation_history: List of conversation records

    Returns:
        Formatted string for LLM prompt
    """
    if not conversation_history:
        return "No previous conversation history."

    formatted_lines = []
    for record in conversation_history[-10:]:  # Last 10 records
        formatted_lines.append(
            f"[{record.timestamp}] {record.source}:\n"
            f"Input: {record.input}\n"
            f"Output: {record.output}\n"
        )

    return "\n".join(formatted_lines)


async def _get_tool_descriptions() -> str:
    """
    Get formatted tool descriptions for prompt template.

    Programmatically retrieves tool descriptions from the MCP server instance
    to avoid hardcoding and ensure consistency with actual registered tools.

    Returns:
        Formatted string with tool descriptions
    """
    try:
        # Import the global MCP server instance
        from mcp_as_a_judge.server import mcp

        # Get the tool manager from the FastMCP server
        tool_manager = mcp._tool_manager

        # Get all registered tools
        tools_dict = {}
        for tool_name, tool_info in tool_manager._tools.items():
            # Extract description from the tool info
            description = tool_info.description or f"Tool: {tool_name}"
            tools_dict[tool_name] = description

        # Format as markdown list
        formatted_descriptions = []
        for tool_name, description in sorted(tools_dict.items()):
            formatted_descriptions.append(f"- **{tool_name}**: {description}")

        return "\n".join(formatted_descriptions)

    except Exception as e:
        logger.warning(f"⚠️ Failed to get tool descriptions programmatically: {e}")
        # Fallback to static descriptions
        return """
- **set_coding_task**: Create or update task metadata (entry point for all coding work)
- **judge_coding_plan**: Validate coding plan with mandatory code analysis requirements
- **judge_testing_implementation**: Validate testing implementation and test coverage (mandatory after implementation)
- **judge_code_change**: Validate COMPLETE code implementations (only when all code is ready for review)
- **judge_coding_task_completion**: Final validation of task completion against requirements
- **raise_obstacle**: Handle obstacles that prevent task completion
- **raise_missing_requirements**: Handle unclear or incomplete requirements
"""




"""
Shared LLM workflow navigation system for enhanced MCP as a Judge.

This module provides the core calculate_next_stage function that ALL tools
use to provide consistent, context-aware workflow navigation based on task history
and current state.
"""

import json
from copy import deepcopy
from typing import Any

from pydantic import BaseModel, Field

from mcp_as_a_judge.core.constants import MAX_TOKENS
from mcp_as_a_judge.core.logging_config import get_logger
from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.messaging.llm_provider import llm_provider
from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskSize, TaskState

# Set up logger using custom get_logger function
logger = get_logger(__name__)


def should_skip_planning(task_metadata: TaskMetadata) -> bool:
    """
    Determine if planning should be skipped based on task size.

    Args:
        task_metadata: Task metadata containing size information

    Returns:
        True if planning should be skipped (XS/S tasks), False otherwise
    """
    return task_metadata.task_size in [TaskSize.XS, TaskSize.S]


class WorkflowGuidance(BaseModel):
    """
    Canonical workflow guidance model used across the system.

    Returned by tools to provide consistent next steps and instructions for
    the coding assistant. This is the single source of truth for the
    WorkflowGuidance schema.
    """

    next_tool: str | None = Field(
        default=None,
        description="Next tool to call, or None if workflow complete",
    )
    reasoning: str = Field(
        default="", description="Clear explanation of why this tool should be used next"
    )
    preparation_needed: list[str] = Field(
        default_factory=list,
        description="List of things that need to be prepared before calling the recommended tool",
    )
    guidance: str = Field(
        default="",
        description="Detailed step-by-step guidance for the AI assistant",
    )

    # Research requirement determination for new tasks (only populated when task is CREATED)
    research_required: bool | None = Field(
        default=None,
        description="Whether research is required for this task (only determined for new CREATED tasks)",
    )
    research_scope: str | None = Field(
        default=None,
        description="Research scope: 'none', 'light', or 'deep' (only determined for new CREATED tasks)",
    )
    research_rationale: str | None = Field(
        default=None,
        description="Explanation of research requirements (only determined for new CREATED tasks)",
    )
    internal_research_required: bool | None = Field(
        default=None,
        description="Whether internal codebase analysis is needed (only determined for new CREATED tasks)",
    )
    risk_assessment_required: bool | None = Field(
        default=None,
        description="Whether risk assessment is needed (only determined for new CREATED tasks)",
    )

    # Backward compatibility property
    @property
    def instructions(self) -> str:
        """Backward compatibility property that maps to guidance field."""
        return self.guidance


class WorkflowGuidanceUserVars(BaseModel):
    """Variables for workflow guidance user prompt."""

    task_id: str = Field(description="Task ID (primary key)")
    task_title: str = Field(description="Task title")
    task_description: str = Field(description="Task description")
    user_requirements: str = Field(description="Current user requirements")
    current_state: str = Field(description="Current task state")
    state_description: str = Field(description="Description of current state")
    current_operation: str = Field(description="Current operation being performed")
    task_size: str = Field(description="Task size classification (xs, s, m, l, xl)")
    task_size_definitions: str = Field(
        description="Task size classifications and workflow routing rules"
    )
    state_transitions: str = Field(description="State transition diagram")
    tool_descriptions: str = Field(description="Available tool descriptions")
    allowed_tool_names: list[str] = Field(
        default_factory=list, description="Closed list of valid tool names"
    )
    allowed_tool_names_json: str = Field(
        default="[]",
        description="JSON array of valid tool names (for strict selection)",
    )
    conversation_context: str = Field(description="Formatted conversation history")
    operation_context: str = Field(description="Current operation context")
    response_schema: str = Field(
        description="JSON schema for the expected response format"
    )


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
    logger.info(f"Calculating next stage for task {task_metadata.task_id}")

    try:
        # Check for deterministic task size routing for CREATED state
        if task_metadata.state == TaskState.CREATED and should_skip_planning(
            task_metadata
        ):
            logger.info(
                f"Task size {task_metadata.task_size.value} - skipping planning phase, proceeding to implementation"
            )
            # XS/S tasks skip planning but still need implementation → code review → testing → completion
            # For deterministic tests, do not prescribe next tool; provide guidance only
            return WorkflowGuidance(
                next_tool=None,
                reasoning=(
                    f"Task size is {task_metadata.task_size.value.upper()} - planning phase can be skipped for simple fixes and minor features."
                ),
                preparation_needed=[
                    "Identify files to modify",
                    "Implement minimal changes",
                    "Write and run tests",
                ],
                guidance=(
                    "Proceed directly to implementation. Once changes are complete and tests pass, continue with the workflow: "
                    "call judge_code_change for code review, then judge_testing_implementation for testing validation, and finally judge_coding_task_completion for final validation."
                ),
            )

        # Deterministic routing for set_coding_task updates: do not send the agent
        # back to planning if the task is already beyond planning states.
        if current_operation.startswith("set_coding_task"):
            if task_metadata.state in (TaskState.PLAN_APPROVED, TaskState.IMPLEMENTING):
                return WorkflowGuidance(
                    next_tool="judge_code_change",
                    reasoning="Plan approved; proceed with implementation and submit changes for review.",
                    preparation_needed=[
                        "Implement according to the approved plan",
                        "Prepare a unified Git diff patch including ALL modified files",
                    ],
                    guidance=(
                        "Continue implementation. When ready, generate a unified Git diff that includes ALL modified files and call judge_code_change (include file_path only if a single file is modified)."
                    ),
                )
            if task_metadata.state == TaskState.REVIEW_READY:
                return WorkflowGuidance(
                    next_tool="judge_testing_implementation",
                    reasoning="Implementation is review-ready; validate testing to progress.",
                    preparation_needed=[
                        "Ensure tests exist and are passing",
                        "Collect raw test output and coverage info",
                    ],
                    guidance=(
                        "Run tests and ensure they pass, then call judge_testing_implementation with a summary of tests and results."
                    ),
                )
            if task_metadata.state == TaskState.TESTING:
                return WorkflowGuidance(
                    next_tool="judge_testing_implementation",
                    reasoning="Task is in testing; validate tests to move forward.",
                    preparation_needed=["Run tests and capture results"],
                    guidance=(
                        "Call judge_testing_implementation with details on implemented tests and their results."
                    ),
                )
            if task_metadata.state == TaskState.COMPLETED:
                return WorkflowGuidance(
                    next_tool=None,
                    reasoning="Task already completed.",
                    preparation_needed=[],
                    guidance="No further action required.",
                )

        # From here on, defer navigation to LLM prompt logic (dynamic, state-aware)

        # Load and format conversation history for LLM context
        # Use task_id as session_id for conversation history
        recent_records = (
            await conversation_service.load_filtered_context_for_enrichment(
                session_id=task_metadata.task_id
            )
        )
        conversation_context = _format_conversation_for_llm(
            conversation_service.format_conversation_history_as_json_array(
                recent_records
            )
        )

        # Research requirements are determined by LLM through prompts when needed
        # For now, we'll let the calling tools handle research requirement setting
        # TODO: Add proper LLM-based research inference using create_separate_messages pattern

        # Import here to avoid import cycle at module import time
        from mcp_as_a_judge.models import SystemVars

        # Get tool descriptions and state info for the prompt
        tool_descriptions = await _get_tool_descriptions()
        available_name_set = await _get_available_tool_names()
        available_tool_names = sorted(available_name_set)
        state_info = task_metadata.get_current_state_info()

        # Prepare operation context
        operation_context = []
        if validation_result:
            operation_context.append(f"- Validation Result: {validation_result}")
        if completion_result:
            operation_context.append(f"- Completion Result: {completion_result}")
        if accumulated_changes:
            operation_context.append(
                f"- Accumulated Changes: {len(accumulated_changes)} files modified"
            )

        # Add file tracking information
        if task_metadata.modified_files:
            operation_context.append(
                f"- Modified Files ({len(task_metadata.modified_files)}): {', '.join(task_metadata.modified_files)}"
            )

            # Check implementation progress (code review happens once implementation changes are ready; tests are validated separately)
            if (
                len(task_metadata.modified_files) > 0
                and task_metadata.state == TaskState.IMPLEMENTING
            ):
                if len(task_metadata.test_files) == 0:
                    operation_context.append(
                        "- IMPLEMENTATION PROGRESS: Implementation files have been created. Continue implementing ALL code AND write tests. Ensure tests are passing before calling judge_code_change."
                    )
                else:
                    operation_context.append(
                        "- IMPLEMENTATION + TESTS: Both implementation and test files exist. Ensure ALL tests are passing, then call judge_code_change for code review."
                    )

        # Add testing information
        if task_metadata.test_files:
            operation_context.append(
                f"- Test Files ({len(task_metadata.test_files)}): {', '.join(task_metadata.test_files)}"
            )
            test_coverage = task_metadata.get_test_coverage_summary()
            operation_context.append(
                f"- Test Status: {test_coverage['test_status']} (All passing: {test_coverage['all_tests_passing']})"
            )

            # Check if testing validation is complete
            if (
                task_metadata.state == TaskState.TESTING
                and test_coverage["all_tests_passing"]
            ):
                operation_context.append(
                    "- TESTING VALIDATION READY: All tests are passing. Ready for judge_testing_implementation to validate test results."
                )

        # Add research guidance based on requirements
        if task_metadata.research_required is True:
            research_status = (
                "completed" if task_metadata.research_completed else "pending"
            )
            operation_context.append(
                f"- RESEARCH REQUIRED (scope: {task_metadata.research_scope}, status: {research_status}): Focus on authoritative, domain-relevant sources. Rationale: {task_metadata.research_rationale}"
            )
        elif task_metadata.research_required is False:
            operation_context.append(
                "- RESEARCH OPTIONAL: Research is optional for this task. If provided, prioritize domain-relevant, authoritative sources."
            )
        else:
            operation_context.append(
                "- RESEARCH STATUS: Research requirements not yet determined (will be inferred for new tasks)."
            )

        operation_context_str = (
            "\n".join(operation_context)
            if operation_context
            else "- No additional context"
        )

        # Use existing llm_provider to get LLM guidance
        logger.info(
            f"Sending navigation request to LLM for task {task_metadata.task_id}"
        )

        # Use the same messaging pattern as other tools
        from mcp.types import SamplingMessage

        # Load task size definitions from shared file
        from mcp_as_a_judge.prompting.loader import (
            create_separate_messages,
            prompt_loader,
        )

        task_size_definitions = prompt_loader.render_prompt(
            "shared/task_size_definitions.md"
        )

        # Build a dynamic response schema that constrains next_tool to allowed tools
        base_schema = WorkflowGuidance.model_json_schema()
        dynamic_schema = deepcopy(base_schema)
        try:
            props = dynamic_schema.get("properties", {})
            if "next_tool" in props:
                # Preserve description if present
                desc = props["next_tool"].get("description", "Next tool to call")
                props["next_tool"] = {
                    "anyOf": [
                        {"type": "string", "enum": available_tool_names},
                        {"type": "null"},
                    ],
                    "description": desc,
                }
        except Exception:
            # Fall back silently to base schema if anything goes wrong
            dynamic_schema = base_schema

        # Create system and user variables for the workflow guidance
        system_vars = SystemVars(
            response_schema=json.dumps(dynamic_schema),
            task_size_definitions=task_size_definitions,
            max_tokens=MAX_TOKENS,
        )
        user_vars = WorkflowGuidanceUserVars(
            task_id=task_metadata.task_id,
            task_title=task_metadata.title,
            task_description=task_metadata.description,
            user_requirements=task_metadata.user_requirements,
            current_state=task_metadata.state.value,
            state_description=state_info["description"],
            current_operation=current_operation,
            task_size=task_metadata.task_size.value,
            task_size_definitions=task_size_definitions,
            state_transitions="CREATED → PLANNING → PLAN_APPROVED → IMPLEMENTING → REVIEW_READY → TESTING → COMPLETED",
            tool_descriptions=tool_descriptions,
            allowed_tool_names=available_tool_names,
            allowed_tool_names_json=json.dumps(available_tool_names),
            conversation_context=conversation_context,
            operation_context=operation_context_str,
            response_schema=json.dumps(dynamic_schema, indent=2),
        )

        # Create messages using the established pattern with dedicated workflow guidance prompts
        messages: list[SamplingMessage] = create_separate_messages(
            "system/workflow_guidance.md",  # Dedicated system prompt for workflow guidance
            "user/workflow_guidance.md",  # Existing user prompt for workflow guidance
            system_vars,
            user_vars,
        )

        response = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,  # type: ignore[arg-type]
            max_tokens=MAX_TOKENS,  # Use standardized constant for comprehensive responses
            prefer_sampling=True,  # Factory handles all message format decisions
        )

        # Parse the JSON response using the existing DRY method
        from mcp_as_a_judge.core.server_helpers import extract_json_from_response

        try:
            logger.info(f"Raw LLM response length: {len(response)}")
            logger.info(f"Raw LLM response preview: {response[:300]}...")

            json_content = extract_json_from_response(response)
            logger.info(f"Extracted JSON content length: {len(json_content)}")
            logger.info(f"Extracted JSON preview: {json_content[:200]}...")

            navigation_data = json.loads(json_content)
            logger.info(f"Parsed JSON keys: {list(navigation_data.keys())}")

        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"❌ Failed to parse LLM response: {e}")
            logger.error(f"❌ Raw response: {response[:500]}...")
            raise ValueError(f"Failed to parse workflow guidance response: {e}") from e

        # Validate required fields
        required_fields = ["next_tool", "reasoning", "preparation_needed", "guidance"]
        missing_fields = [
            field for field in required_fields if field not in navigation_data
        ]
        if missing_fields:
            raise ValueError(
                f"Missing required fields in LLM response: {missing_fields}"
            )

        # Normalize next_tool (convert "null" string to None) and validate
        if navigation_data["next_tool"] in ["null", "None", ""]:
            navigation_data["next_tool"] = None

        normalized_next_tool = _normalize_next_tool_name(
            navigation_data.get("next_tool"), task_metadata, set(available_tool_names)
        )

        workflow_guidance = WorkflowGuidance(
            next_tool=normalized_next_tool,
            reasoning=navigation_data.get("reasoning", ""),
            preparation_needed=navigation_data.get("preparation_needed", []),
            guidance=navigation_data.get("guidance", ""),
            # Research determination fields (only populated for new CREATED tasks)
            research_required=navigation_data.get("research_required"),
            research_scope=navigation_data.get("research_scope"),
            research_rationale=navigation_data.get("research_rationale"),
            internal_research_required=navigation_data.get(
                "internal_research_required"
            ),
            risk_assessment_required=navigation_data.get("risk_assessment_required"),
        )

        # Fallback: if next_tool missing/None and not completed, route to get_current_coding_task
        if (
            workflow_guidance.next_tool is None
            and task_metadata.state != TaskState.COMPLETED
        ):
            if "get_current_coding_task" in available_name_set:
                workflow_guidance.next_tool = "get_current_coding_task"
            else:
                # As a last resort, pick judge_coding_plan for created/planning; judge_code_change otherwise
                if task_metadata.state in (TaskState.CREATED, TaskState.PLANNING):
                    workflow_guidance.next_tool = "judge_coding_plan"
                elif task_metadata.state in (
                    TaskState.PLAN_APPROVED,
                    TaskState.IMPLEMENTING,
                    TaskState.REVIEW_READY,
                ):
                    workflow_guidance.next_tool = "judge_code_change"
                elif task_metadata.state == TaskState.TESTING:
                    workflow_guidance.next_tool = "judge_testing_implementation"

        logger.info(
            f"Calculated next stage: next_tool={workflow_guidance.next_tool}, "
            f"instructions_length={len(workflow_guidance.instructions)}"
        )

        return workflow_guidance

    except Exception as e:
        logger.error(
            f"Failed to calculate next stage for task {task_metadata.task_id}: {e}"
        )

        # Debug: Log the actual response if available
        if "response" in locals():
            logger.error(f"Full LLM response length: {len(response)}")
            logger.error(f"Full LLM response: {response}")

            # Check if response is truncated (doesn't end with proper JSON closing)
            if not response.strip().endswith("}"):
                logger.error("Response appears to be truncated - doesn't end with '}'")

            # Try to see if we can extract partial JSON
            try:
                from mcp_as_a_judge.core.server_helpers import (
                    extract_json_from_response,
                )

                json_content = extract_json_from_response(response)
                logger.error(f"Extracted JSON: {json_content}")
            except Exception as extract_error:
                logger.error(f"JSON extraction also failed: {extract_error}")

        # Return fallback navigation with appropriate next tool based on state
        fallback_next_tool: str | None = "judge_coding_plan"  # Default fallback
        if (
            task_metadata.state == TaskState.PLAN_APPROVED
            or task_metadata.state == TaskState.IMPLEMENTING
            or task_metadata.state == TaskState.REVIEW_READY
        ):
            fallback_next_tool = "judge_code_change"
        elif task_metadata.state == TaskState.TESTING:
            fallback_next_tool = "judge_testing_implementation"
        elif task_metadata.state == TaskState.COMPLETED:
            fallback_next_tool = None  # Only case where null is appropriate

        return WorkflowGuidance(
            next_tool=fallback_next_tool,
            reasoning="Error occurred during workflow calculation, providing fallback based on current state",
            preparation_needed=[
                "Review the error and task state",
                "Ensure all prerequisites are met",
            ],
            guidance=f"Error calculating next stage: {e!s}. Fallback recommendation based on current state ({task_metadata.state}). Please review task manually and proceed with the suggested next tool if appropriate.",
        )


def _format_conversation_for_llm(conversation_history: list[dict[str, Any]]) -> str:
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
        ts = record.get("timestamp")
        src = record.get("source")
        inp = record.get("input")
        out = record.get("output")
        formatted_lines.append(f"[{ts}] {src}:\nInput: {inp}\nOutput: {out}\n")

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

        # Use the public FastMCP API to list tools
        tools = await mcp.list_tools()

        # Format as markdown list
        formatted_descriptions: list[str] = []
        for t in sorted(tools, key=lambda x: x.name):
            description = t.description or f"Tool: {t.name}"
            formatted_descriptions.append(f"- **{t.name}**: {description}")

        return "\n".join(formatted_descriptions)

    except Exception as e:
        logger.warning(f"Failed to get tool descriptions programmatically: {e}")
        # Fallback to static descriptions
        return """
- **set_coding_task**: Create or update task metadata (entry point for all coding work)
- **judge_coding_plan**: Validate coding plans with conditional research, internal analysis (when applicable), and risk assessment
- **judge_testing_implementation**: Validate testing implementation and test coverage (mandatory after implementation)
- **judge_code_change**: Validate COMPLETE code implementations (only when all code is ready for review)
- **judge_coding_task_completion**: Final validation of task completion against requirements
- **raise_obstacle**: Handle obstacles that prevent task completion
- **raise_missing_requirements**: Handle unclear or incomplete requirements
"""


async def _get_available_tool_names() -> set[str]:
    """Return the set of registered tool names using the FastMCP server API.

    Falls back to a static set if the server object is unavailable.
    """
    try:
        from mcp_as_a_judge.server import mcp  # Local import to avoid cycles

        # Use the public async API to list tools
        tools = await mcp.list_tools()
        return {t.name for t in tools}
    except Exception:
        # Conservative fallback to known tools in this project
        return {
            "set_coding_task",
            "get_current_coding_task",
            "judge_coding_plan",
            "judge_code_change",
            "judge_testing_implementation",
            "judge_coding_task_completion",
            "raise_obstacle",
            "raise_missing_requirements",
        }


def _normalize_next_tool_name(
    next_tool_raw: str | None, task_metadata: TaskMetadata, available: set[str]
) -> str | None:
    """Normalize and validate the next_tool name produced by the LLM.

    - Fix common typos/synonyms (e.g., "judge_code_chnage" → "judge_code_change",
      "implement_coding_plan" → "judge_code_change").
    - Ensure the final value exists in the registered tool set.
    - If still invalid, choose a sensible fallback based on the task state.
    """
    if not next_tool_raw:
        return None

    candidate = next_tool_raw.strip()
    # Normalize case and whitespace
    key = candidate.lower().replace(" ", "_")

    # Minimal, surgical synonym/typo map based on observed LLM outputs
    synonyms: dict[str, str] = {
        # Typos
        "judge_code_chnage": "judge_code_change",
        # Misinterpreted actions (implementation is not a tool; route to code review gate)
        "implement_coding_plan": "judge_code_change",
    }

    mapped = synonyms.get(key, key)

    # Guardrail: avoid spurious routing back to set_coding_task
    if mapped == "set_coding_task":
        # During planning/created, keep planning loop unless the user explicitly updates requirements
        if task_metadata.state in (TaskState.CREATED, TaskState.PLANNING):
            return "judge_coding_plan"
        if task_metadata.state in (
            TaskState.PLAN_APPROVED,
            TaskState.IMPLEMENTING,
            TaskState.REVIEW_READY,
        ):
            return "judge_code_change"
        if task_metadata.state == TaskState.TESTING:
            return "judge_testing_implementation"
        if task_metadata.state == TaskState.COMPLETED:
            return None

    # Guardrail: avoid premature completion calls — route to the correct gate
    if mapped == "judge_coding_task_completion":
        if task_metadata.state in (TaskState.CREATED, TaskState.PLANNING):
            return "judge_coding_plan"
        if task_metadata.state in (
            TaskState.PLAN_APPROVED,
            TaskState.IMPLEMENTING,
            TaskState.REVIEW_READY,
        ):
            return "judge_code_change"
        if task_metadata.state == TaskState.TESTING:
            return "judge_testing_implementation"
        if task_metadata.state == TaskState.COMPLETED:
            return None

    if mapped in available:
        return mapped

    # If still invalid, choose a fallback consistent with current state
    # Mirror the fallback used in exception handling for consistency
    if task_metadata.state in (
        TaskState.PLAN_APPROVED,
        TaskState.IMPLEMENTING,
        TaskState.REVIEW_READY,
    ):
        return "judge_code_change"
    if task_metadata.state == TaskState.TESTING:
        return "judge_testing_implementation"
    if task_metadata.state == TaskState.COMPLETED:
        return None

    # Default conservative fallback: let the system recover the active task id/state
    return "get_current_coding_task"

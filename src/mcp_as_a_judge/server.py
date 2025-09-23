"""
MCP as a Judge server implementation.

This module contains the main MCP server with judge tools for validating
coding plans and code changes against software engineering best practices.
"""

import builtins
import contextlib
import json
import time

from mcp.server.fastmcp import Context, FastMCP
from pydantic import ValidationError

from mcp_as_a_judge.core.constants import MAX_TOKENS
from mcp_as_a_judge.core.logging_config import (
    get_context_aware_logger,
    get_logger,
    log_startup_message,
    log_tool_execution,
    set_context_reference,
    setup_logging,
)
from mcp_as_a_judge.core.server_helpers import (
    evaluate_coding_plan,
    extract_changed_files,
    extract_json_from_response,
    generate_dynamic_elicitation_model,
    generate_validation_error_message,
    initialize_llm_configuration,
    looks_like_unified_diff,
    validate_research_quality,
    validate_test_output,
)
from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.db.db_config import load_config
from mcp_as_a_judge.elicitation import elicitation_provider
from mcp_as_a_judge.messaging.llm_provider import llm_provider

# Import the complete JudgeCodingPlanUserVars from models.py
from mcp_as_a_judge.models import (
    JudgeCodeChangeUserVars,
    SystemVars,
    WorkflowGuidance,
)
from mcp_as_a_judge.models.enhanced_responses import (
    EnhancedResponseFactory,
    JudgeResponse,
    TaskAnalysisResult,
    TaskCompletionResult,
)
from mcp_as_a_judge.models.task_metadata import (
    TaskMetadata,
    TaskSize,
    TaskState,
)
from mcp_as_a_judge.prompting.loader import create_separate_messages
from mcp_as_a_judge.tasks.manager import (
    create_new_coding_task,
    save_task_metadata_to_history,
    update_existing_coding_task,
)
from mcp_as_a_judge.tool_description.factory import (
    tool_description_provider,
)
from mcp_as_a_judge.workflow import calculate_next_stage

setup_logging("INFO")
mcp = FastMCP(name="MCP-as-a-Judge")
initialize_llm_configuration()

config = load_config()
conversation_service = ConversationHistoryService(config)
log_startup_message(config)
logger = get_logger(__name__)
context_logger = get_context_aware_logger(__name__)


@mcp.tool(description=tool_description_provider.get_description("set_coding_task"))  # type: ignore[misc,unused-ignore]
async def set_coding_task(
    user_request: str,
    task_title: str,
    task_description: str,
    ctx: Context,
    task_size: TaskSize = TaskSize.M,  # Task size classification (xs, s, m, l, xl) - defaults to Medium for backward compatibility
    # FOR UPDATING EXISTING TASKS ONLY
    task_id: str = "",  # REQUIRED when updating existing task
    user_requirements: str = "",  # Updates current requirements
    state: TaskState = TaskState.CREATED,  # Optional: update task state with validation when updating existing task
    # OPTIONAL
    tags: list[str] = [],  # noqa: B006
) -> TaskAnalysisResult:
    """Create or update coding task metadata with enhanced workflow management."""
    task_id_for_logging = task_id if task_id else "new_task"

    # Initialize mutable default (no longer needed since tags has default [])
    # if tags is None:
    #     tags = []

    # Set global context reference for system-wide logging
    set_context_reference(ctx)

    # Log tool execution start using context-aware logger
    await context_logger.info(f"set_coding_task called for task: {task_id_for_logging}")

    original_input = {
        "user_request": user_request,
        "task_title": task_title,
        "task_description": task_description,
        "task_id": task_id,
        "user_requirements": user_requirements,
        "tags": tags,
        "state": state.value if isinstance(state, TaskState) else state,
    }

    try:
        if task_id:
            task_metadata = await update_existing_coding_task(
                task_id=task_id,
                user_request=user_request,
                task_title=task_title,
                task_description=task_description,
                user_requirements=user_requirements,
                state=state,  # Allow optional state transition with validation
                tags=tags,
                conversation_service=conversation_service,
            )
            action = "updated"
            context_summary = f"Updated coding task '{task_metadata.title}' (ID: {task_metadata.task_id})"

        else:
            task_metadata = await create_new_coding_task(
                user_request=user_request,
                task_title=task_title,
                task_description=task_description,
                user_requirements=user_requirements if user_requirements else "",
                tags=tags,
                conversation_service=conversation_service,
                task_size=task_size,
            )
            action = "created"
            context_summary = f"Created new coding task '{task_metadata.title}' (ID: {task_metadata.task_id})"
        workflow_guidance = await calculate_next_stage(
            task_metadata=task_metadata,
            current_operation=f"set_coding_task_{action}",
            conversation_service=conversation_service,
            ctx=ctx,
        )

        # Apply research requirements determined by LLM workflow guidance (for new tasks)
        if action == "created" and workflow_guidance.research_required is not None:
            from mcp_as_a_judge.models.task_metadata import ResearchScope

            task_metadata.research_required = workflow_guidance.research_required
            task_metadata.research_rationale = (
                workflow_guidance.research_rationale or ""
            )

            # Map research scope string to enum
            if workflow_guidance.research_scope:
                scope_mapping = {
                    "none": ResearchScope.NONE,
                    "light": ResearchScope.LIGHT,
                    "deep": ResearchScope.DEEP,
                }
                task_metadata.research_scope = scope_mapping.get(
                    workflow_guidance.research_scope.lower(), ResearchScope.NONE
                )

            # Set internal research and risk assessment requirements
            if workflow_guidance.internal_research_required is not None:
                task_metadata.internal_research_required = (
                    workflow_guidance.internal_research_required
                )
            if workflow_guidance.risk_assessment_required is not None:
                task_metadata.risk_assessment_required = (
                    workflow_guidance.risk_assessment_required
                )
            if workflow_guidance.design_patterns_enforcement is not None:
                task_metadata.design_patterns_enforcement = (
                    workflow_guidance.design_patterns_enforcement
                )

            # Update timestamp to reflect changes
            task_metadata.updated_at = int(time.time())

            logger.info(
                f"Applied LLM-determined research requirements: required={task_metadata.research_required}, scope={task_metadata.research_scope}, rationale='{task_metadata.research_rationale}'"
            )

        # Save task metadata to conversation history using task_id as primary key
        await save_task_metadata_to_history(
            task_metadata=task_metadata,
            user_request=user_request,
            action=action,
            conversation_service=conversation_service,
        )

        result = EnhancedResponseFactory.create_task_analysis_result(
            action=action,
            context_summary=context_summary,
            current_task_metadata=task_metadata,
            workflow_guidance=workflow_guidance,
        )

        await conversation_service.save_tool_interaction_and_cleanup(
            session_id=task_metadata.task_id,
            tool_name="set_coding_task",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(
                result.model_dump(
                    mode="json",
                    exclude_unset=True,
                    exclude_none=True,
                    exclude_defaults=True,
                )
            ),
        )

        return result

    except Exception as e:
        # Create error response
        error_metadata = TaskMetadata(
            title=task_title,
            description=task_description,
            user_requirements=user_requirements if user_requirements else "",
            state=TaskState.CREATED,
            task_size=TaskSize.M,
            tags=tags,
        )

        error_guidance = WorkflowGuidance(
            next_tool="get_current_coding_task",
            reasoning="Task update failed or task_id not found; retrieve the latest valid task_id and metadata.",
            preparation_needed=[
                "Call get_current_coding_task to fetch active task_id",
                "Retry with the returned task_id if needed",
            ],
            guidance=(
                f"Error occurred: {e!s}. Use get_current_coding_task to retrieve the most recent task_id, then retry the operation with that ID."
            ),
        )

        error_result = EnhancedResponseFactory.create_task_analysis_result(
            action="error",
            context_summary=f"Error creating/updating task: {e!s}",
            current_task_metadata=error_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction (use task_id if available, otherwise generate one for logging)
        error_task_id = task_id if task_id else error_metadata.task_id
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=error_task_id,
                tool_name="set_coding_task",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    error_result.model_dump(
                        mode="json",
                        exclude_unset=True,
                        exclude_none=True,
                        exclude_defaults=True,
                    )
                ),
            )

        return error_result


@mcp.tool(
    description=tool_description_provider.get_description("get_current_coding_task")
)  # type: ignore[misc,unused-ignore]
async def get_current_coding_task(ctx: Context) -> dict:
    """Return the most recently active coding task's task_id and metadata.

    Use this when you lost the UUID. If none exists, the response includes
    guidance to call set_coding_task to create a new task.
    """
    set_context_reference(ctx)
    log_tool_execution("get_current_coding_task", "unknown")

    try:
        recent = await conversation_service.db.get_recent_sessions(limit=1)
        if not recent:
            return {
                "found": False,
                "feedback": "No existing coding task sessions found. Call set_coding_task to create a task and obtain a task_id UUID.",
                "workflow_guidance": {
                    "next_tool": "set_coding_task",
                    "reasoning": "No recent sessions in conversation history",
                    "preparation_needed": [
                        "Provide user_request, task_title, task_description"
                    ],
                    "guidance": "Call set_coding_task to initialize a new task. Use the returned task_id UUID in all subsequent tool calls.",
                },
            }

        task_id, last_activity = recent[0]

        # Load task metadata from history if available
        from mcp_as_a_judge.tasks.manager import load_task_metadata_from_history

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id, conversation_service=conversation_service
        )

        response: dict = {
            "found": True,
            "task_id": task_id,
            "last_activity": last_activity,
        }

        if task_metadata is not None:
            response["current_task_metadata"] = task_metadata.model_dump(
                mode="json",
                exclude_unset=True,
                exclude_none=True,
                exclude_defaults=True,
            )

            # Generate workflow guidance for the current task state
            from mcp_as_a_judge.workflow.workflow_guidance import calculate_next_stage

            workflow_guidance = await calculate_next_stage(
                task_metadata=task_metadata,
                current_operation="get_current_coding_task_found",
                conversation_service=conversation_service,
                ctx=ctx,
            )

            response["workflow_guidance"] = workflow_guidance.model_dump(
                mode="json",
                exclude_unset=True,
                exclude_none=True,
                exclude_defaults=True,
            )
        else:
            response["note"] = (
                "Task metadata not found in history for this session, but a session exists. Use this task_id UUID and proceed; if validation fails, recreate with set_coding_task."
            )
            # Provide basic workflow guidance even without metadata
            response["workflow_guidance"] = {
                "next_tool": "set_coding_task",
                "reasoning": "Task metadata not found in history, may need to recreate task",
                "preparation_needed": [
                    "Verify task_id is correct",
                    "If validation fails, recreate with set_coding_task",
                ],
                "guidance": "Try using this task_id with other tools. If validation fails, call set_coding_task to recreate the task with proper metadata.",
            }

        return response
    except Exception as e:
        return {
            "found": False,
            "error": f"Failed to retrieve current task: {e!s}",
            "workflow_guidance": {
                "next_tool": "set_coding_task",
                "reasoning": "Error while retrieving recent sessions",
                "preparation_needed": [
                    "Provide user_request, task_title, task_description"
                ],
                "guidance": "Call set_coding_task to initialize a new task and use its task_id UUID going forward.",
            },
        }


@mcp.tool(description=tool_description_provider.get_description("raise_obstacle"))  # type: ignore[misc,unused-ignore]
async def raise_obstacle(
    problem: str,
    research: str,
    options: list[str],
    ctx: Context,
    task_id: str = "",  # OPTIONAL: Task ID for context and memory
    # Optional HITL assistance inputs
    decision_area: str = "",
    constraints: list[str] = [],  # noqa: B006
) -> str:
    """Obstacle handling tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("raise_obstacle", task_id if task_id else "unknown")

    # Store original input for saving later
    original_input = {
        "problem": problem,
        "research": research,
        "options": options,
        "task_id": task_id,
        "decision_area": decision_area,
        "constraints": constraints,
    }

    try:
        # Load task metadata to get current context
        from mcp_as_a_judge.tasks.manager import load_task_metadata_from_history

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id if task_id else "test_task",
            conversation_service=conversation_service,
        )

        if not task_metadata:
            # Create minimal task metadata for obstacle handling
            task_metadata = TaskMetadata(
                title="Obstacle Resolution",
                description=f"Handling obstacle: {problem}",
                user_requirements="Resolve obstacle to continue task",
                state=TaskState.BLOCKED,
                task_size=TaskSize.M,
                tags=["obstacle"],
            )

        # Update task state to BLOCKED
        task_metadata.update_state(TaskState.BLOCKED)

        formatted_options = "\n".join(
            f"{i + 1}. {option}" for i, option in enumerate(options)
        )

        context_info = (
            "Agent encountered an obstacle and needs user decision on how to proceed"
        )
        info_extra = []
        if decision_area:
            info_extra.append(f"Decision area: {decision_area}")
        if constraints:
            info_extra.append("Constraints: " + ", ".join(constraints))
        information_needed = (
            "User needs to choose from available options and provide any additional context"
            + (". " + "; ".join(info_extra) if info_extra else "")
        )
        current_understanding = (
            f"Problem: {problem}. Research: {research}. Options: {formatted_options}"
        )

        dynamic_model = await generate_dynamic_elicitation_model(
            context_info, information_needed, current_understanding, ctx
        )

        # Use elicitation provider with capability checking
        elicit_result = await elicitation_provider.elicit_user_input(
            message=f"""OBSTACLE ENCOUNTERED

Problem: {problem}

Research Done: {research}

Available Options:
{formatted_options}

Decision Area: {decision_area if decision_area else "Not specified"}

Constraints:
{chr(10).join(f"- {c}" for c in constraints) if constraints else "None provided"}

Please choose an option (by number or description) and provide any additional context or modifications you'd like.""",
            schema=dynamic_model,
            ctx=ctx,
        )

        if elicit_result.success:
            # Handle successful elicitation response
            user_response = elicit_result.data

            # Ensure user_response is a dictionary
            if not isinstance(user_response, dict):
                user_response = {"user_input": str(user_response)}  # type: ignore[unreachable]

            # Format the response data for display
            response_summary = []
            for field_name, field_value in user_response.items():
                if field_value:  # Only include non-empty values
                    formatted_key = field_name.replace("_", " ").title()
                    response_summary.append(f"**{formatted_key}:** {field_value}")

            response_text = (
                "\n".join(response_summary)
                if response_summary
                else "User provided response"
            )

            # HITL tools should always direct to set_coding_task to update requirements
            workflow_guidance = WorkflowGuidance(
                next_tool="set_coding_task",
                reasoning="Obstacle resolved through user interaction. Task requirements may need updating based on the resolution.",
                preparation_needed=[
                    "Review the obstacle resolution",
                    "Update task requirements if needed",
                ],
                guidance="Call set_coding_task to update the task with any new requirements or clarifications from the obstacle resolution. Then continue with the workflow.",
            )

            # Create resolution text
            result_text = f"✅ OBSTACLE RESOLVED: {response_text}"

            # Save successful interaction as conversation record
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_metadata.task_id,  # Use task_id as primary key
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    {"obstacle_acknowledged": True, "message": result_text}
                ),
            )

            return result_text

        else:
            # Elicitation failed or not available - return the fallback message
            workflow_guidance = WorkflowGuidance(
                next_tool=None,
                reasoning="Obstacle elicitation failed or unavailable",
                preparation_needed=["Manual intervention required"],
                guidance=f"Obstacle not resolved: {elicit_result.message}. Manual intervention required.",
            )

            # Save failed interaction
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_metadata.task_id,  # Use task_id as primary key
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    {"obstacle_acknowledged": False, "message": elicit_result.message}
                ),
            )

            return (
                f"❌ ERROR: Failed to elicit user decision: {elicit_result.message}. "
                f"No messaging providers available"
            )

    except Exception as e:
        # Create error response
        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred while handling obstacle",
            preparation_needed=["Review error details", "Manual intervention required"],
            guidance=f"Error handling obstacle: {e!s}. Manual intervention required.",
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_metadata.task_id
                if "task_metadata" in locals() and task_metadata
                else (task_id if task_id else "unknown"),
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    {
                        "obstacle_acknowledged": False,
                        "message": f"❌ ERROR: Failed to elicit user decision. Error: {e!s}. Cannot resolve obstacle without user input.",
                    }
                ),
            )

        return (
            f"❌ ERROR: Failed to elicit user decision. Error: {e!s}. "
            f"No messaging providers available"
        )


@mcp.tool(
    description=tool_description_provider.get_description("raise_missing_requirements")
)  # type: ignore[misc,unused-ignore]
async def raise_missing_requirements(
    current_request: str,
    identified_gaps: list[str],
    specific_questions: list[str],
    task_id: str,  # REQUIRED: Task ID for context and memory
    ctx: Context,
    # Optional HITL assistance inputs
    decision_areas: list[str] = [],  # noqa: B006
    options: list[str] = [],  # noqa: B006
    constraints: list[str] = [],  # noqa: B006
) -> str:
    """Requirements clarification tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("raise_missing_requirements", task_id)

    # Store original input for saving later
    original_input = {
        "current_request": current_request,
        "identified_gaps": identified_gaps,
        "specific_questions": specific_questions,
        "task_id": task_id,
        "decision_areas": decision_areas,
        "options": options,
        "constraints": constraints,
    }

    try:
        # Load task metadata to get current context
        from mcp_as_a_judge.tasks.manager import load_task_metadata_from_history

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        if not task_metadata:
            # Create minimal task metadata for requirements clarification
            task_metadata = TaskMetadata(
                title="Requirements Clarification",
                description=f"Clarifying requirements: {current_request}",
                user_requirements=current_request,
                state=TaskState.CREATED,
                task_size=TaskSize.M,
                tags=["requirements"],
            )

        # Format the gaps and questions for clarity
        formatted_gaps = "\n".join(f"• {gap}" for gap in identified_gaps)
        formatted_questions = "\n".join(
            f"{i + 1}. {question}" for i, question in enumerate(specific_questions)
        )

        context_info = "Agent needs clarification on user requirements and confirmation of key decisions to proceed"
        info_extra = []
        if decision_areas:
            info_extra.append("Decisions to confirm: " + ", ".join(decision_areas))
        if constraints:
            info_extra.append("Constraints: " + ", ".join(constraints))
        information_needed = (
            "Clarified requirements, answers to specific questions, and priority levels"
            + (". " + "; ".join(info_extra) if info_extra else "")
        )
        current_understanding = (
            f"Current request: {current_request}. Gaps: {formatted_gaps}. Questions: {formatted_questions}"
            + (f". Candidate options: {'; '.join(options or [])}" if options else "")
        )

        dynamic_model = await generate_dynamic_elicitation_model(
            context_info, information_needed, current_understanding, ctx
        )

        # Use elicitation provider with capability checking
        elicit_result = await elicitation_provider.elicit_user_input(
            message=f"""REQUIREMENTS CLARIFICATION NEEDED

Current Understanding: {current_request}

Identified Requirement Gaps:
{formatted_gaps}

Specific Questions:
{formatted_questions}

Decisions To Confirm:
{chr(10).join(f"- {a}" for a in decision_areas) if decision_areas else "None provided"}

Candidate Options:
{chr(10).join(f"- {o}" for o in options) if options else "None provided"}

Constraints:
{chr(10).join(f"- {c}" for c in constraints) if constraints else "None provided"}

Please provide clarified requirements and indicate their priority level (high/medium/low).""",
            schema=dynamic_model,
            ctx=ctx,
        )

        if elicit_result.success:
            # Handle successful elicitation response
            user_response = elicit_result.data

            # Ensure user_response is a dictionary
            if not isinstance(user_response, dict):
                user_response = {"user_input": str(user_response)}  # type: ignore[unreachable]

            # Format the response data for display
            response_summary = []
            for field_name, field_value in user_response.items():
                if field_value:  # Only include non-empty values
                    formatted_key = field_name.replace("_", " ").title()
                    response_summary.append(f"**{formatted_key}:** {field_value}")

            response_text = (
                "\n".join(response_summary)
                if response_summary
                else "User provided clarifications"
            )

            # Update task metadata with clarified requirements
            clarified_requirements = (
                f"{current_request}\n\nClarifications: {response_text}"
            )
            task_metadata.update_requirements(
                clarified_requirements, source="clarification"
            )

            # HITL tools should always direct to set_coding_task to update requirements

            # Save successful interaction
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    {
                        "clarification_needed": False,
                        "message": f"✅ REQUIREMENTS CLARIFIED: {response_text}",
                    }
                ),
            )
            return f"✅ REQUIREMENTS CLARIFIED: {response_text}"

        else:
            # Elicitation failed or not available - return the fallback message

            # Save failed interaction
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    {
                        "clarification_needed": True,
                        "message": elicit_result.message,
                    }
                ),
            )
            return (
                f"❌ ERROR: Failed to elicit requirement clarifications. Error: {elicit_result.message}. "
                f"No messaging providers available"
            )

    except Exception as e:
        # Create error response

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    {
                        "clarification_needed": True,
                        "message": f"❌ ERROR: Failed to elicit requirement clarifications. Error: {e!s}. Cannot proceed without clear requirements.",
                    }
                ),
            )
        # Ensure we have non-None metadata for typing
        if "task_metadata" not in locals() or task_metadata is None:
            task_metadata = TaskMetadata(
                title="Requirements Clarification",
                description=f"Clarifying requirements: {current_request}",
                user_requirements=current_request,
                state=TaskState.CREATED,
                task_size=TaskSize.M,
                tags=["requirements"],
            )

        return (
            f"❌ ERROR: Failed to elicit requirement clarifications. Error: {e!s}. "
            f"No messaging providers available"
        )


@mcp.tool(
    description=tool_description_provider.get_description(
        "judge_coding_task_completion"
    )
)  # type: ignore[misc,unused-ignore]
async def judge_coding_task_completion(
    task_id: str,  # REQUIRED: Task ID for context and validation
    completion_summary: str,
    requirements_met: list[str],
    implementation_details: str,
    ctx: Context,
    # OPTIONAL
    remaining_work: list[str] = [],  # noqa: B006
    quality_notes: str = "",
    testing_status: str = "",
) -> TaskCompletionResult:
    """Final validation tool for coding task completion."""
    # Log tool execution start
    log_tool_execution("judge_coding_task_completion", task_id)

    # Store original input for saving later
    original_input = {
        "task_id": task_id,
        "completion_summary": completion_summary,
        "requirements_met": requirements_met,
        "implementation_details": implementation_details,
        "remaining_work": remaining_work,
        "quality_notes": quality_notes,
        "testing_status": testing_status,
    }

    try:
        # Load task metadata to get current context
        from mcp_as_a_judge.tasks.manager import load_task_metadata_from_history

        logger.info(
            f"judge_coding_task_completion: Loading task metadata for task_id: {task_id}"
        )

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        logger.info(
            f"judge_coding_task_completion: Task metadata loaded: {task_metadata is not None}"
        )
        if task_metadata:
            logger.info(
                f"judge_coding_task_completion: Task state: {task_metadata.state}, title: {task_metadata.title}"
            )
        else:
            conversation_history = (
                await conversation_service.load_filtered_context_for_enrichment(
                    task_id, "", ctx
                )
            )
            logger.info(
                f"judge_coding_task_completion: Conversation history entries: {len(conversation_history)}"
            )
            for entry in conversation_history[-5:]:
                logger.info(
                    f"judge_coding_task_completion: History entry: {entry.source} at {entry.timestamp}"
                )

        if not task_metadata:
            # Create a minimal task metadata for debugging
            task_metadata = TaskMetadata(
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements="Task requirements not found",
                state=TaskState.COMPLETED,  # Appropriate state for completion check
                task_size=TaskSize.M,
                tags=["debug", "missing-metadata"],
            )

            # Return debug information
            return TaskCompletionResult(
                approved=False,
                feedback=f"Task {task_id} not found in conversation history. This usually means set_coding_task was not called first, or the server was restarted and lost the in-memory data.",
                current_task_metadata=task_metadata,
                workflow_guidance=WorkflowGuidance(
                    next_tool="get_current_coding_task",
                    reasoning="Task metadata not found; recover the active task context before proceeding.",
                    preparation_needed=[
                        "Call get_current_coding_task to fetch the active task_id",
                        "Retry completion or proceed per recovered state",
                    ],
                    guidance=(
                        "Use get_current_coding_task to retrieve the most recent task_id and metadata. Then continue the workflow based on the recovered state (typically judge_code_change → judge_testing_implementation → judge_coding_task_completion)."
                    ),
                ),
            )

        # STEP 1: Validate approvals from judge tools
        completion_readiness = task_metadata.validate_completion_readiness()
        approval_status = completion_readiness["approval_status"]
        missing_approvals = completion_readiness["missing_approvals"]

        # STEP 2: Check if all requirements are met
        has_remaining_work = remaining_work and len(remaining_work) > 0
        requirements_coverage = len(requirements_met) > 0

        # STEP 3: Determine if task is complete (now includes approval validation)
        task_complete = (
            completion_readiness["ready_for_completion"]  # All approvals validated
            and requirements_coverage
            and not has_remaining_work
            and completion_summary.strip() != ""
        )

        if task_complete:
            # Task is complete - update state to COMPLETED
            task_metadata.update_state(TaskState.COMPLETED)

            feedback = f"""✅ TASK COMPLETION APPROVED

**Completion Summary:** {completion_summary}

**Requirements Satisfied:**
{chr(10).join(f"• {req}" for req in requirements_met)}

**Implementation Details:** {implementation_details}

**✅ APPROVAL VALIDATION PASSED:**
• Plan Approved: {"✅" if approval_status["plan_approved"] else "❌"} {f"({approval_status['plan_approved_at']})" if approval_status["plan_approved_at"] else ""}
• Code Files Approved: {"✅" if approval_status["all_modified_files_approved"] else "❌"} ({approval_status["code_files_approved"]}/{len(task_metadata.modified_files)} files)
• Testing Approved: {"✅" if approval_status["testing_approved"] else "❌"} {f"({approval_status['testing_approved_at']})" if approval_status["testing_approved_at"] else ""}"""

            if quality_notes:
                feedback += f"\n\n**Quality Notes:** {quality_notes}"

            if testing_status:
                feedback += f"\n\n**Testing Status:** {testing_status}"

            feedback += (
                "\n\n🎉 **Task successfully completed with all required approvals!**"
            )

            # Update state to COMPLETED when task completion is approved
            task_metadata.update_state(TaskState.COMPLETED)

            workflow_guidance = await calculate_next_stage(
                task_metadata=task_metadata,
                current_operation="judge_coding_task_completion_approved",
                conversation_service=conversation_service,
                ctx=ctx,
            )

            result = TaskCompletionResult(
                approved=True,
                feedback=feedback,
                required_improvements=[],
                current_task_metadata=task_metadata,
                workflow_guidance=workflow_guidance,
            )

        else:
            # Task is not complete - provide guidance for remaining work
            task_metadata.update_state(TaskState.IMPLEMENTING)

            feedback = f"""⚠️ TASK COMPLETION NOT APPROVED

**Current Progress:** {completion_summary}

**Requirements Satisfied:**
{chr(10).join(f"• {req}" for req in requirements_met) if requirements_met else "• None specified"}"""

            required_improvements = []

            # APPROVAL VALIDATION FAILURES
            if not completion_readiness["ready_for_completion"]:
                feedback += "\n\n**❌ APPROVAL VALIDATION FAILED:**"
                feedback += f"\n{completion_readiness['validation_message']}"
                feedback += "\n\n**Missing Approvals:**"
                for missing in missing_approvals:
                    feedback += f"\n• {missing}"
                required_improvements.extend(missing_approvals)

                # Detailed approval status
                feedback += "\n\n**Current Approval Status:**"
                feedback += f"\n• Plan Approved: {'✅' if approval_status['plan_approved'] else '❌'}"
                feedback += f"\n• Code Files Approved: {approval_status['code_files_approved']}/{len(task_metadata.modified_files)} files"
                feedback += f"\n• Testing Approved: {'✅' if approval_status['testing_approved'] else '❌'}"

            # OTHER COMPLETION ISSUES
            if has_remaining_work and remaining_work:
                feedback += f"\n\n**Remaining Work:**\n{chr(10).join(f'• {work}' for work in remaining_work)}"
                required_improvements.extend(remaining_work)

            if not requirements_coverage:
                feedback += "\n\n**Issue:** No requirements marked as satisfied"
                required_improvements.append("Specify which requirements have been met")

            if not completion_summary.strip():
                feedback += "\n\n**Issue:** No completion summary provided"
                required_improvements.append("Provide a detailed completion summary")

            feedback += "\n\n📋 **Complete all required approvals and remaining work before resubmitting for final approval.**"

            # Deterministic next step based on missing approvals
            next_tool = None
            if any("plan approval" in m for m in missing_approvals):
                next_tool = "judge_coding_plan"
            elif any("code approval" in m for m in missing_approvals) or (
                approval_status.get("code_files_approved", 0)
                < len(task_metadata.modified_files or [])
            ):
                next_tool = "judge_code_change"
            elif any("testing approval" in m for m in missing_approvals):
                next_tool = "judge_testing_implementation"
            else:
                # Default to code review gate for safety
                next_tool = "judge_code_change"

            # Construct guidance tailored to the required step
            if next_tool == "judge_coding_plan":
                reasoning = "Missing plan approval; revise and resubmit the plan."
                prep = [
                    "Address required improvements in the plan",
                    "Ensure design, file list, and research coverage are complete",
                ]
                guidance = "Update the plan addressing all feedback and call judge_coding_plan. After approval, proceed to implementation and code review."
            elif next_tool == "judge_code_change":
                reasoning = "Code has not been reviewed/approved; submit implementation for review."
                prep = [
                    "Implement or finalize code changes per requirements",
                    "Prepare file paths and a concise change summary",
                ]
                guidance = "Call judge_code_change with the modified files and a concise summary or diff. After approval, implement/verify tests and validate via judge_testing_implementation."
            else:  # judge_testing_implementation
                reasoning = "Testing approval missing; run and validate tests."
                prep = [
                    "Run the test suite and capture results",
                    "Provide coverage details if available",
                ]
                guidance = "Call judge_testing_implementation with test files, execution results, and coverage details. After approval, resubmit completion."

            workflow_guidance = WorkflowGuidance(
                next_tool=next_tool,
                reasoning=reasoning,
                preparation_needed=prep,
                guidance=guidance,
            )

            result = TaskCompletionResult(
                approved=False,
                feedback=feedback,
                required_improvements=required_improvements,
                current_task_metadata=task_metadata,
                workflow_guidance=workflow_guidance,
            )

        # Save successful interaction
        await conversation_service.save_tool_interaction_and_cleanup(
            session_id=task_id,  # Use task_id as primary key
            tool_name="judge_coding_task_completion",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(
                result.model_dump(
                    mode="json",
                    exclude_unset=True,
                    exclude_none=True,
                    exclude_defaults=True,
                )
            ),
        )

        return result

    except Exception as e:
        # Create error response
        error_guidance = WorkflowGuidance(
            next_tool="get_current_coding_task",
            reasoning="Error occurred; recover active task context and continue with the correct step.",
            preparation_needed=[
                "Call get_current_coding_task to fetch active task_id",
                "Retry with the returned task_id or proceed based on recovered state",
            ],
            guidance=f"Error validating task completion: {e!s}. Use get_current_coding_task to recover the current task_id and continue the workflow (judge_code_change → judge_testing_implementation → judge_coding_task_completion).",
        )

        # Create minimal task metadata for error case
        if "task_metadata" in locals() and task_metadata is not None:
            error_metadata = task_metadata
        else:
            error_metadata = TaskMetadata(
                title="Error Task",
                description="Error occurred during completion validation",
                user_requirements="Error occurred before task metadata could be loaded",
                state=TaskState.IMPLEMENTING,
                task_size=TaskSize.M,
                tags=["error"],
            )

        error_result = TaskCompletionResult(
            approved=False,
            feedback=f"❌ ERROR: Failed to validate task completion. Error: {e!s}",
            required_improvements=["Fix the error and try again"],
            current_task_metadata=error_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_id,
                tool_name="judge_coding_task_completion",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    error_result.model_dump(
                        mode="json",
                        exclude_unset=True,
                        exclude_none=True,
                        exclude_defaults=True,
                    )
                ),
            )

        return error_result


@mcp.tool(description=tool_description_provider.get_description("judge_coding_plan"))  # type: ignore[misc,unused-ignore]
async def judge_coding_plan(
    plan: str,
    design: str,
    research: str,
    research_urls: list[str],
    ctx: Context,
    task_id: str = "",
    context: str = "",
    # OPTIONAL override
    user_requirements: str = "",
    # OPTIONAL explicit inputs to avoid rejection on missing deliverables
    problem_domain: str = "",
    problem_non_goals: list[str] = [],  # noqa: B006
    library_plan: list[dict] = [],  # noqa: B006
    internal_reuse_components: list[dict] = [],  # noqa: B006
    design_patterns: list[dict] = [],  # noqa: B006
    identified_risks: list[str] = [],  # noqa: B006
    risk_mitigation_strategies: list[str] = [],  # noqa: B006
) -> JudgeResponse:
    """Coding plan evaluation tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("judge_coding_plan", task_id if task_id else "test_task")

    # Store original input for saving later
    original_input = {
        "task_id": task_id if task_id else "test_task",
        "plan": plan,
        "design": design,
        "research": research,
        "context": context,
        "research_urls": research_urls,
        "problem_domain": problem_domain,
        "problem_non_goals": problem_non_goals,
        "library_plan": library_plan,
        "internal_reuse_components": internal_reuse_components,
        "design_patterns": design_patterns,
    }

    try:
        # If neither MCP sampling nor LLM API are available, short-circuit with a clear error
        sampling_available = llm_provider.is_sampling_available(ctx)
        llm_available = llm_provider.is_llm_api_available()
        if not (sampling_available or llm_available):
            minimal_metadata = TaskMetadata(
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements=user_requirements if user_requirements else "",
                state=TaskState.CREATED,
                task_size=TaskSize.M,
                tags=["debug", "missing-metadata"],
            )
            return EnhancedResponseFactory.create_judge_response(
                approved=False,
                feedback=(
                    "Error during coding plan evaluation: No messaging providers available"
                ),
                required_improvements=["Error occurred during review"],
                current_task_metadata=minimal_metadata,
                workflow_guidance=WorkflowGuidance(
                    next_tool=None,
                    reasoning="No messaging providers available",
                    preparation_needed=["Configure MCP sampling or LLM API"],
                    guidance="Set up a provider and retry the evaluation.",
                ),
            )
        # Load task metadata to get current context and user requirements
        from mcp_as_a_judge.tasks.manager import load_task_metadata_from_history

        logger.info(
            f"judge_coding_plan: Loading task metadata for task_id: {task_id if task_id else 'test_task'}"
        )

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id if task_id else "test_task",
            conversation_service=conversation_service,
        )

        logger.info(
            f"judge_coding_plan: Task metadata loaded: {task_metadata is not None}"
        )
        if task_metadata:
            logger.info(
                f"judge_coding_plan: Task state: {task_metadata.state}, title: {task_metadata.title}"
            )
        else:
            conversation_history = (
                await conversation_service.load_filtered_context_for_enrichment(
                    task_id if task_id else "test_task", "", ctx
                )
            )
            logger.info(
                f"judge_coding_plan: Conversation history entries: {len(conversation_history)}"
            )
            for entry in conversation_history[-5:]:
                logger.info(
                    f"judge_coding_plan: History entry: {entry.source} at {entry.timestamp}"
                )

        if not task_metadata:
            # Create a minimal task metadata fallback but continue evaluation
            task_metadata = TaskMetadata(
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements="Task requirements not found",
                state=TaskState.CREATED,
                task_size=TaskSize.M,
                tags=["debug", "missing-metadata"],
            )

        # Transition to PLANNING state when planning starts
        if task_metadata.state == TaskState.CREATED:
            task_metadata.update_state(TaskState.PLANNING)

        # Derive user requirements from task metadata (allow override)
        user_requirements = (
            user_requirements
            if user_requirements is not None
            else task_metadata.user_requirements
        )

        effective_identified_risks = list(
            identified_risks or task_metadata.identified_risks or []
        )
        effective_risk_mitigations = list(
            risk_mitigation_strategies or task_metadata.risk_mitigation_strategies or []
        )

        # Clean up risk assessment data if required
        if task_metadata.risk_assessment_required:
            cleaned_risks = [
                risk.strip()
                for risk in effective_identified_risks
                if isinstance(risk, str) and risk.strip()
            ]
            cleaned_mitigations = [
                mitigation.strip()
                for mitigation in effective_risk_mitigations
                if isinstance(mitigation, str) and mitigation.strip()
            ]

            # Ensure 1:1 mapping between risks and mitigations
            if len(cleaned_mitigations) < len(cleaned_risks):
                for _ in range(len(cleaned_mitigations), len(cleaned_risks)):
                    cleaned_mitigations.append(
                        "Document concrete mitigation strategy for this risk"
                    )
            elif len(cleaned_mitigations) > len(cleaned_risks):
                cleaned_mitigations = cleaned_mitigations[: len(cleaned_risks)]

            effective_identified_risks = cleaned_risks
            effective_risk_mitigations = cleaned_mitigations

        if (
            task_metadata.risk_assessment_required
            and effective_identified_risks
            and not task_metadata.identified_risks
        ):
            task_metadata.identified_risks = list(effective_identified_risks)
        if (
            task_metadata.risk_assessment_required
            and effective_risk_mitigations
            and not task_metadata.risk_mitigation_strategies
        ):
            task_metadata.risk_mitigation_strategies = list(effective_risk_mitigations)

        original_input["identified_risks"] = effective_identified_risks
        original_input["risk_mitigation_strategies"] = effective_risk_mitigations

        # NOTE: Conditional research, internal analysis, and risk assessment requirements
        # are now determined dynamically by the LLM through the workflow guidance system
        # rather than using hardcoded rule-based analysis

        research_required = bool(task_metadata.research_required)
        auto_approved_due_to_limit = False

        # DYNAMIC RESEARCH VALIDATION - Only validate if research is actually required
        if research_required and not task_metadata.has_exceeded_plan_rejection_limit():
            # Import dynamic research analysis functions
            from mcp_as_a_judge.tasks.research import (
                analyze_research_requirements,
                update_task_metadata_with_analysis,
                validate_url_adequacy,
            )

            # Step 1: Perform research requirements analysis if not already done
            if task_metadata.expected_url_count is None:
                logger.info(
                    f"Performing dynamic research requirements analysis for task {task_id or 'test_task'}"
                )
                try:
                    requirements_analysis = await analyze_research_requirements(
                        task_metadata=task_metadata,
                        user_requirements=user_requirements,
                        ctx=ctx,
                    )
                    # Update task metadata with analysis results
                    update_task_metadata_with_analysis(
                        task_metadata, requirements_analysis
                    )
                    logger.info(
                        f"Research analysis complete: Expected={task_metadata.expected_url_count}, Minimum={task_metadata.minimum_url_count}"
                    )

                    # Save the analysis results to task history
                    await save_task_metadata_to_history(
                        task_metadata=task_metadata,
                        user_request=user_requirements,
                        action="research_requirements_analyzed",
                        conversation_service=conversation_service,
                    )
                except Exception as e:
                    logger.error(
                        f"❌ Research analysis failed: {e}. Using fallback validation."
                    )
                    # Fall back to basic empty check if analysis fails
                    if not research_urls or len(research_urls) == 0:
                        validation_issue = f"Research is required (scope: {task_metadata.research_scope}). No research URLs provided. Rationale: {task_metadata.research_rationale}"
                        context_info = f"User requirements: {user_requirements}. Plan: {plan[:200]}..."

                        descriptive_feedback = await generate_validation_error_message(
                            validation_issue, context_info, ctx
                        )

                        # Increment rejection count for insufficient research
                        task_metadata.increment_plan_rejection()
                        logger.info(
                            f"Plan rejected due to insufficient research. Rejection count: {task_metadata.plan_rejection_count}/1"
                        )

                        workflow_guidance = await calculate_next_stage(
                            task_metadata=task_metadata,
                            current_operation="judge_coding_plan_insufficient_research",
                            conversation_service=conversation_service,
                            ctx=ctx,
                        )

                        return JudgeResponse(
                            approved=False,
                            required_improvements=[
                                "Research required but no URLs provided",
                            ],
                            feedback=descriptive_feedback,
                            current_task_metadata=task_metadata,
                            workflow_guidance=workflow_guidance,
                        )

            # Step 2: Validate provided URLs against dynamic requirements
            if task_metadata.expected_url_count is not None:
                url_validation = await validate_url_adequacy(
                    provided_urls=research_urls,
                    expected_count=task_metadata.expected_url_count,
                    minimum_count=task_metadata.minimum_url_count or 1,
                    reasoning=task_metadata.url_requirement_reasoning,
                    ctx=ctx,
                )

                if not url_validation.adequate:
                    logger.warning(
                        f"⚠️ URL validation failed for task {task_id or 'test_task'}: {url_validation.feedback}"
                    )

                    descriptive_feedback = await generate_validation_error_message(
                        url_validation.feedback,
                        f"User requirements: {user_requirements}. Research scope: {task_metadata.research_scope}",
                        ctx,
                    )

                    # Increment rejection count for URL validation failure
                    task_metadata.increment_plan_rejection()
                    logger.info(
                        f"Plan rejected due to insufficient URL count. Rejection count: {task_metadata.plan_rejection_count}/1"
                    )

                    workflow_guidance = await calculate_next_stage(
                        task_metadata=task_metadata,
                        current_operation="judge_coding_plan_insufficient_research",
                        conversation_service=conversation_service,
                        ctx=ctx,
                    )

                    return JudgeResponse(
                        approved=False,
                        required_improvements=[
                            f"Provide at least {url_validation.minimum_count} research URLs",
                        ],
                        feedback=descriptive_feedback,
                        current_task_metadata=task_metadata,
                        workflow_guidance=workflow_guidance,
                    )
                else:
                    logger.info(
                        f"✅ URL validation passed for task {task_id}: {url_validation.provided_count} URLs meet requirements"
                    )

            # Research URLs provided - mark completion and let LLM prompts handle quality validation
            task_metadata.research_completed = int(time.time())
            task_metadata.updated_at = int(time.time())

            # Save updated task metadata
            await save_task_metadata_to_history(
                task_metadata=task_metadata,
                user_request=user_requirements,
                action="research_completed",
                conversation_service=conversation_service,
            )

        elif research_required:
            logger.info(
                "Skipping research validation because plan rejection limit was reached; "
                "auto-approval safeguard will handle the workflow progression."
            )
        else:
            # Research is optional - log but don't block
            logger.info(
                f"Research optional for task {task_id} (research_required={task_metadata.research_required})"
            )
            if research_urls:
                logger.info(f"Optional research provided: {len(research_urls)} URLs")

        # HITL is guided by workflow prompts and elicitation tools, not rule-based gating here

        # STEP 1: Load conversation history and format as JSON array
        conversation_history = (
            await conversation_service.load_filtered_context_for_enrichment(
                task_id or "test_task", "", ctx
            )
        )
        history_json_array = (
            conversation_service.format_conversation_history_as_json_array(
                conversation_history
            )
        )

        # STEP 4: Use helper function for main evaluation with JSON array conversation history
        # Provide contextual note to avoid blocking on non-existent internal components
        eval_context = ""
        try:
            if (
                task_metadata.internal_research_required is True
                and not task_metadata.related_code_snippets
            ):
                eval_context = (
                    "No repository-local related components are currently identified in task metadata. "
                    "If none can be found in this repository, do not block on internal codebase analysis; "
                    "set internal_research_required=false in current_task_metadata and proceed with clear rationale."
                )
        except Exception:
            # Be resilient; context is optional
            eval_context = ""

        # Check rejection limit - auto-approve if already rejected once
        if task_metadata.has_exceeded_plan_rejection_limit():
            auto_approved_due_to_limit = True
            logger.info(
                f"Plan has already been rejected {task_metadata.plan_rejection_count} time(s). "
                f"Auto-approving to prevent endless iteration cycles."
            )

            # Create auto-approval result
            evaluation_result = EnhancedResponseFactory.create_judge_response(
                approved=True,
                feedback="Plan auto-approved after reaching rejection limit (max 1 rejection allowed). "
                "Moving forward to prevent endless iteration cycles.",
                required_improvements=[],
                current_task_metadata=task_metadata,
                workflow_guidance=WorkflowGuidance(
                    next_tool=None,
                    reasoning="Auto-approved due to rejection limit",
                    preparation_needed=[],
                    guidance="Proceed with implementation",
                ),
            )
        else:
            # Perform normal evaluation
            evaluation_result = await evaluate_coding_plan(
                plan,
                design,
                research,
                research_urls,
                user_requirements,
                eval_context,
                history_json_array,
                task_metadata,  # Pass task metadata for conditional features
                ctx,
                problem_domain=problem_domain,
                problem_non_goals=problem_non_goals,
                library_plan=library_plan,
                internal_reuse_components=internal_reuse_components,
                design_patterns=design_patterns,
                identified_risks_override=effective_identified_risks,
                risk_mitigation_override=effective_risk_mitigations,
            )

        # Additional research validation if approved
        if evaluation_result.approved and not auto_approved_due_to_limit:
            research_validation_result = await validate_research_quality(
                research, research_urls, plan, design, user_requirements, ctx
            )
            if research_validation_result:
                # Increment rejection count for research validation failure
                task_metadata.increment_plan_rejection()
                logger.info(
                    f"Plan rejected due to research validation failure. Rejection count: {task_metadata.plan_rejection_count}/1"
                )

                workflow_guidance = await calculate_next_stage(
                    task_metadata=task_metadata,
                    current_operation="judge_coding_plan_research_failed",
                    conversation_service=conversation_service,
                    ctx=ctx,
                )

                return JudgeResponse(
                    approved=False,
                    required_improvements=research_validation_result.get(
                        "required_improvements", []
                    ),
                    feedback=research_validation_result.get(
                        "feedback", "Research validation failed"
                    ),
                    current_task_metadata=task_metadata,
                    workflow_guidance=workflow_guidance,
                )

        # Use the updated task metadata from the evaluation result (includes conditional requirements)
        updated_task_metadata = evaluation_result.current_task_metadata

        # Enforce mandatory planning deliverables: problem_domain and library_plan
        # If missing but the plan was approved, convert to required improvements
        missing_deliverables: list[str] = []
        try:
            # Fill from explicit inputs if LLM omitted them in metadata
            if (
                problem_domain
                and not getattr(updated_task_metadata, "problem_domain", "").strip()
            ):
                updated_task_metadata.problem_domain = problem_domain
            if problem_non_goals and not getattr(
                updated_task_metadata, "problem_non_goals", None
            ):
                updated_task_metadata.problem_non_goals = problem_non_goals
            if library_plan and (
                not getattr(updated_task_metadata, "library_plan", None)
                or len(getattr(updated_task_metadata, "library_plan", [])) == 0
            ):
                # Convert dict list to LibraryPlanItem list
                library_plan_items = [
                    TaskMetadata.LibraryPlanItem(**item) for item in library_plan
                ]
                updated_task_metadata.library_plan = library_plan_items
            if internal_reuse_components and (
                not getattr(updated_task_metadata, "internal_reuse_components", None)
                or len(getattr(updated_task_metadata, "internal_reuse_components", []))
                == 0
            ):
                # Convert dict list to ReuseComponent list
                reuse_components = [
                    TaskMetadata.ReuseComponent(**item)
                    for item in internal_reuse_components
                ]
                updated_task_metadata.internal_reuse_components = reuse_components
            if effective_identified_risks and not getattr(
                updated_task_metadata, "identified_risks", []
            ):
                updated_task_metadata.identified_risks = effective_identified_risks
            if effective_risk_mitigations and not getattr(
                updated_task_metadata, "risk_mitigation_strategies", []
            ):
                updated_task_metadata.risk_mitigation_strategies = (
                    effective_risk_mitigations
                )

            # Now check for missing deliverables
            if not getattr(updated_task_metadata, "problem_domain", "").strip():
                missing_deliverables.append(
                    "Add a clear Problem Domain Statement with explicit non-goals"
                )
            if (
                not getattr(updated_task_metadata, "library_plan", [])
                or len(getattr(updated_task_metadata, "library_plan", [])) == 0
            ):
                missing_deliverables.append(
                    "Provide a Library Selection Map (purpose → internal/external library with justification)"
                )
        except Exception:  # nosec B110
            pass

        if auto_approved_due_to_limit:
            # Preserve auto-approval even if optional deliverables are missing
            effective_approved = True
        else:
            effective_approved = evaluation_result.approved and not missing_deliverables
        effective_required_improvements = list(evaluation_result.required_improvements)
        if missing_deliverables:
            # Merge missing deliverables to required improvements
            effective_required_improvements.extend(missing_deliverables)

        # Preserve canonical task_id so we never drift across sessions due to LLM outputs
        canonical_task_id = None
        if task_metadata and getattr(task_metadata, "task_id", None):
            canonical_task_id = task_metadata.task_id
        elif task_id:
            canonical_task_id = task_id

        if (
            canonical_task_id
            and getattr(updated_task_metadata, "task_id", None) != canonical_task_id
        ):
            with contextlib.suppress(Exception):
                # Overwrite to ensure consistency across conversation history and routing
                updated_task_metadata.task_id = canonical_task_id

        # Calculate workflow guidance for the effective outcome
        # Build a synthetic validation_result with the effective approval and improvements
        synthetic_eval = EnhancedResponseFactory.create_judge_response(
            approved=effective_approved,
            feedback=evaluation_result.feedback,
            required_improvements=effective_required_improvements,
            current_task_metadata=updated_task_metadata,
            workflow_guidance=WorkflowGuidance(
                next_tool=None,
                reasoning="",
                preparation_needed=[],
                guidance="",
            ),
        )
        workflow_guidance = await calculate_next_stage(
            task_metadata=updated_task_metadata,
            current_operation="judge_coding_plan_completed",
            conversation_service=conversation_service,
            ctx=ctx,
            validation_result=synthetic_eval,
        )

        # Deterministic next step for coding plan outcome to avoid loops
        if effective_approved:
            # Mark plan as approved for completion validation and update state
            updated_task_metadata.mark_plan_approved()
            updated_task_metadata.update_state(TaskState.PLAN_APPROVED)

            # Delete previous failed plan attempts, keeping only the most recent approved one
            await conversation_service.db.delete_previous_plan(
                updated_task_metadata.task_id
            )

            # Force next step to code review implementation gate
            workflow_guidance.next_tool = "judge_code_change"
            if not workflow_guidance.reasoning:
                workflow_guidance.reasoning = (
                    "Plan approved; proceed with implementation and code review."
                )
            if not workflow_guidance.preparation_needed:
                workflow_guidance.preparation_needed = [
                    "Implement according to the approved plan",
                    "Prepare file paths and change summary for review",
                ]
            if not workflow_guidance.guidance:
                workflow_guidance.guidance = "Start implementation. When a cohesive set of changes is ready, call judge_code_change with file paths and a concise summary or diff."
        else:
            # Increment rejection count for tracking
            updated_task_metadata.increment_plan_rejection()
            logger.info(
                f"Plan rejected. Rejection count: {updated_task_metadata.plan_rejection_count}/1"
            )

            # Keep/return to planning state and request plan improvements
            updated_task_metadata.update_state(TaskState.PLANNING)
            workflow_guidance.next_tool = "judge_coding_plan"
            if not workflow_guidance.reasoning:
                workflow_guidance.reasoning = (
                    "Plan not approved; address feedback and resubmit."
                )
            if not workflow_guidance.preparation_needed:
                workflow_guidance.preparation_needed = [
                    "Revise plan per required improvements",
                    "Ensure design, file list, and research coverage meet requirements",
                ]
            if not workflow_guidance.guidance:
                workflow_guidance.guidance = "Update the plan addressing all required improvements and resubmit to judge_coding_plan."

        result = JudgeResponse(
            approved=effective_approved,
            required_improvements=effective_required_improvements,
            feedback=evaluation_result.feedback,
            current_task_metadata=updated_task_metadata,
            workflow_guidance=workflow_guidance,
        )

        # STEP 3: Save tool interaction to conversation history using the REAL task_id
        save_session_id = (
            (task_metadata.task_id if task_metadata else None)
            or task_id
            or getattr(updated_task_metadata, "task_id", None)
            or "test_task"
        )
        await conversation_service.save_tool_interaction_and_cleanup(
            session_id=save_session_id,  # Always prefer real task_id
            tool_name="judge_coding_plan",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(
                result.model_dump(
                    mode="json",
                    exclude_unset=True,
                    exclude_none=True,
                    exclude_defaults=True,
                )
            ),
        )

        return result

    except Exception as e:
        import traceback

        error_details = (
            f"Error during plan review: {e!s}\nTraceback: {traceback.format_exc()}"
        )
        logger.error(error_details)

        # Create error guidance
        error_guidance = WorkflowGuidance(
            next_tool="get_current_coding_task",
            reasoning="Error occurred during coding plan evaluation; recover active task context and retry.",
            preparation_needed=[
                "Call get_current_coding_task to fetch active task_id",
                "Retry evaluation with the returned task_id",
            ],
            guidance=f"Error during plan review: {e!s}. Use get_current_coding_task to recover the current task_id and retry.",
        )

        # Create minimal task metadata for error case
        if "task_metadata" in locals() and task_metadata is not None:
            error_metadata = task_metadata
            # Increment rejection count for error cases too
            error_metadata.increment_plan_rejection()
            logger.info(
                f"Plan rejected due to error. Rejection count: {error_metadata.plan_rejection_count}/1"
            )
        else:
            error_metadata = TaskMetadata(
                title="Error Task",
                description="Error occurred during plan evaluation",
                user_requirements="Error occurred before task metadata could be loaded",
                state=TaskState.PLANNING,
                task_size=TaskSize.M,
                tags=["error"],
            )

        # For all errors, return enhanced error response
        error_result = JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=f"Error during coding plan evaluation: {e!s}",
            current_task_metadata=error_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=(task_id or "unknown")
                if "task_id" in locals()
                else "unknown",
                tool_name="judge_coding_plan",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    error_result.model_dump(
                        mode="json",
                        exclude_unset=True,
                        exclude_none=True,
                        exclude_defaults=True,
                    )
                ),
            )

        return error_result


@mcp.tool(description=tool_description_provider.get_description("judge_code_change"))  # type: ignore[misc,unused-ignore]
async def judge_code_change(
    code_change: str,
    ctx: Context,
    file_path: str = "File path not specified",
    change_description: str = "Change description not provided",
    task_id: str = "",
    # OPTIONAL override
    user_requirements: str = "",
) -> JudgeResponse:
    """Code change evaluation tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("judge_code_change", task_id if task_id else "test_task")

    # Store original input for saving later
    original_input = {
        "task_id": task_id if task_id else "test_task",
        "code_change": code_change,
        "file_path": file_path,
        "change_description": change_description,
    }

    try:
        # Load task metadata to get current context and user requirements
        from mcp_as_a_judge.tasks.manager import load_task_metadata_from_history

        logger.info(
            f"judge_code_change: Loading task metadata for task_id: {task_id or 'test_task'}"
        )

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id or "test_task",
            conversation_service=conversation_service,
        )

        logger.info(
            f"judge_code_change: Task metadata loaded: {task_metadata is not None}"
        )
        if task_metadata:
            logger.info(
                f"judge_code_change: Task state: {task_metadata.state}, title: {task_metadata.title}"
            )
        else:
            conversation_history = (
                await conversation_service.load_filtered_context_for_enrichment(
                    task_id or "test_task", "", ctx
                )
            )
            logger.info(
                f"judge_code_change: Conversation history entries: {len(conversation_history)}"
            )
            for entry in conversation_history[-5:]:
                logger.info(
                    f"judge_code_change: History entry: {entry.source} at {entry.timestamp}"
                )

        if not task_metadata:
            # Create a minimal task metadata for debugging
            task_metadata = TaskMetadata(
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements="Task requirements not found",
                state=TaskState.IMPLEMENTING,
                task_size=TaskSize.M,
                tags=["debug", "missing-metadata"],
            )

            # Return debug information
            return JudgeResponse(
                approved=False,
                required_improvements=["Task not found in conversation history"],
                feedback=f"Task {task_id} not found in conversation history. This usually means set_coding_task was not called first, or the server was restarted and lost the in-memory data.",
                current_task_metadata=task_metadata,
                workflow_guidance=WorkflowGuidance(
                    next_tool="set_coding_task",
                    reasoning="Task metadata not found in history",
                    preparation_needed=[
                        "Call set_coding_task first to create the task"
                    ],
                    guidance="You must call set_coding_task before calling judge_code_change. The task_id must come from a successful set_coding_task call.",
                ),
            )

        # Transition to IMPLEMENTING state when implementation starts
        if task_metadata.state == TaskState.PLAN_APPROVED:
            task_metadata.update_state(TaskState.IMPLEMENTING)

        # Derive user requirements from task metadata (allow override)
        user_requirements = (
            user_requirements
            if user_requirements is not None
            else task_metadata.user_requirements
        )

        # QUICK VALIDATION: Require a unified Git diff to avoid generic approvals
        if not looks_like_unified_diff(code_change):
            # Do not proceed to LLM; return actionable guidance to provide a diff
            guidance = WorkflowGuidance(
                next_tool="judge_code_change",
                reasoning=(
                    "Code review requires a unified Git diff to evaluate specific changes."
                ),
                preparation_needed=[
                    "Generate a unified Git diff (e.g., `git diff`)",
                    "Include all relevant files in one patch",
                    "Pass it to judge_code_change as `code_change`",
                ],
                guidance=(
                    "Provide a unified Git diff patch of your changes. Avoid narrative summaries. "
                    "Example: run `git diff --unified` and pass the output."
                ),
            )
            return JudgeResponse(
                approved=False,
                required_improvements=[
                    "Provide a unified Git diff patch of the changes for review"
                ],
                feedback=(
                    "The input to judge_code_change must be a unified Git diff (with 'diff --git', '---', '+++', '@@'). "
                    "Received non-diff content; cannot perform a precise code review."
                ),
                current_task_metadata=task_metadata,
                workflow_guidance=guidance,
            )

        # STEP 1: Load conversation history and format as JSON array
        conversation_history = (
            await conversation_service.load_filtered_context_for_enrichment(
                task_id or "test_task", "", ctx
            )
        )
        history_json_array = (
            conversation_service.format_conversation_history_as_json_array(
                conversation_history
            )
        )

        # Extract changed files from unified diff for logging/validation
        changed_files = extract_changed_files(code_change)
        logger.info(
            f"judge_code_change: Files detected in diff ({len(changed_files)}): {', '.join(changed_files)}"
        )

        # STEP 2: Create system and user messages with separate context and conversation history
        system_vars = SystemVars(
            response_schema=json.dumps(JudgeResponse.model_json_schema()),
            max_tokens=MAX_TOKENS,
        )
        user_vars = JudgeCodeChangeUserVars(
            user_requirements=user_requirements,
            code_change=code_change,
            file_path=file_path,
            change_description=change_description,
            context="",  # Empty context for now - can be enhanced later
            conversation_history=history_json_array,  # JSON array with timestamps
        )
        messages = create_separate_messages(
            "system/judge_code_change.md",
            "user/judge_code_change.md",
            system_vars,
            user_vars,
        )

        # STEP 3: Use messaging layer for LLM evaluation
        response_text = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=MAX_TOKENS,
            prefer_sampling=True,
        )

        # Parse the JSON response
        try:
            json_content = extract_json_from_response(response_text)
            judge_result = JudgeResponse.model_validate_json(json_content)

            # Enforce per-file coverage: every changed file must have a reviewed_files entry
            try:
                reviewed_paths = {
                    rf.path for rf in getattr(judge_result, "reviewed_files", [])
                }
            except Exception:
                reviewed_paths = set()
            missing_reviews = [p for p in changed_files if p not in reviewed_paths]
            if missing_reviews:
                logger.warning(
                    f"judge_code_change: Missing per-file reviews for: {', '.join(missing_reviews)}"
                )
                guidance = WorkflowGuidance(
                    next_tool="judge_code_change",
                    reasoning=(
                        "Per-file coverage incomplete: every changed file must be reviewed"
                    ),
                    preparation_needed=[
                        "Enumerate all changed files from the diff",
                        "Add a reviewed_files entry for each with per-file feedback",
                    ],
                    guidance=(
                        "Update the response to include reviewed_files entries for all missing files: "
                        + ", ".join(missing_reviews)
                    ),
                )
                return JudgeResponse(
                    approved=False,
                    required_improvements=[
                        f"Add reviewed_files entries for: {', '.join(missing_reviews)}"
                    ],
                    feedback=(
                        "Incomplete per-file coverage. Provide a reviewed_files entry for each changed file."
                    ),
                    current_task_metadata=task_metadata,
                    workflow_guidance=guidance,
                )

            # Track the file that was reviewed (if approved)
            if judge_result.approved:
                # Add all changed files to modified files and mark as approved
                for p in changed_files:
                    task_metadata.add_modified_file(p)
                    task_metadata.mark_code_approved(p)
                logger.info(f"Marked files as approved: {', '.join(changed_files)}")

                # Update state to TESTING when code is approved
                if task_metadata.state in [
                    TaskState.IMPLEMENTING,
                    TaskState.PLAN_APPROVED,
                ]:
                    task_metadata.update_state(TaskState.TESTING)

            # Calculate workflow guidance
            workflow_guidance = await calculate_next_stage(
                task_metadata=task_metadata,
                current_operation="judge_code_change_completed",
                conversation_service=conversation_service,
                ctx=ctx,
                validation_result=judge_result,
            )

            # Create enhanced response
            result = JudgeResponse(
                approved=judge_result.approved,
                required_improvements=judge_result.required_improvements,
                feedback=judge_result.feedback,
                current_task_metadata=task_metadata,
                workflow_guidance=workflow_guidance,
            )

            # STEP 4: Save tool interaction to conversation history using the REAL task_id
            save_session_id = (
                task_metadata.task_id
                if getattr(task_metadata, "task_id", None)
                else (task_id or "test_task")
            )
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=save_session_id,  # Always prefer real task_id
                tool_name="judge_code_change",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    result.model_dump(
                        mode="json",
                        exclude_unset=True,
                        exclude_none=True,
                        exclude_defaults=True,
                    )
                ),
            )

            return result

        except (ValidationError, ValueError) as e:
            raise ValueError(
                f"Failed to parse code change evaluation response: {e}. Raw response: {response_text}"
            ) from e

    except Exception as e:
        import traceback

        error_details = (
            f"Error during code review: {e!s}\nTraceback: {traceback.format_exc()}"
        )

        # Create error guidance
        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred during code change evaluation",
            preparation_needed=["Review error details", "Check task parameters"],
            guidance=f"Error during code review: {e!s}. Please review and try again.",
        )

        # Create minimal task metadata for error case
        error_metadata = (
            task_metadata
            if "task_metadata" in locals()
            else TaskMetadata(
                title="Error Task",
                description="Error occurred during code evaluation",
                user_requirements="",
                state=TaskState.IMPLEMENTING,
                task_size=TaskSize.M,
                tags=["error"],
            )
        )

        # For all errors, return enhanced error response
        error_result = JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details,
            current_task_metadata=error_metadata,  # type: ignore[arg-type]
            workflow_guidance=error_guidance,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_id or "unknown",
                tool_name="judge_code_change",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    error_result.model_dump(
                        mode="json",
                        exclude_unset=True,
                        exclude_none=True,
                        exclude_defaults=True,
                    )
                ),
            )

        return error_result


@mcp.tool(
    description=tool_description_provider.get_description(
        "judge_testing_implementation"
    )
)  # type: ignore[misc,unused-ignore]
async def judge_testing_implementation(
    task_id: str,  # REQUIRED: Task ID for context and validation
    test_summary: str,
    test_files: list[str],
    test_execution_results: str,
    ctx: Context,
    test_coverage_report: str = "",
    test_types_implemented: list[str] = [],  # noqa: B006
    testing_framework: str = "",
    performance_test_results: str = "",
    manual_test_notes: str = "",
) -> JudgeResponse:
    """Testing implementation validation tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("judge_testing_implementation", task_id)

    # Store original input for saving later
    original_input = {
        "task_id": task_id,
        "test_summary": test_summary,
        "test_files": test_files,
        "test_execution_results": test_execution_results,
        "test_coverage_report": test_coverage_report,
        "test_types_implemented": test_types_implemented,
        "testing_framework": testing_framework,
        "performance_test_results": performance_test_results,
        "manual_test_notes": manual_test_notes,
    }

    try:
        # Load task metadata to get current context
        from mcp_as_a_judge.tasks.manager import load_task_metadata_from_history

        logger.info(
            f"judge_testing_implementation: Loading task metadata for task_id: {task_id}"
        )

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        logger.info(
            f"judge_testing_implementation: Task metadata loaded: {task_metadata is not None}"
        )
        if task_metadata:
            logger.info(
                f"judge_testing_implementation: Task state: {task_metadata.state}, test files: {len(task_metadata.test_files)}"
            )

        if not task_metadata:
            # Create a minimal task metadata for debugging
            task_metadata = TaskMetadata(
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements="Task requirements not found",
                state=TaskState.TESTING,
                task_size=TaskSize.M,
                tags=["debug", "missing-metadata"],
            )

            # Return debug information
            return JudgeResponse(
                approved=False,
                required_improvements=["Task not found in conversation history"],
                feedback=f"Task {task_id} not found in conversation history. This usually means set_coding_task was not called first, or the server was restarted and lost the in-memory data.",
                current_task_metadata=task_metadata,
                workflow_guidance=WorkflowGuidance(
                    next_tool="set_coding_task",
                    reasoning="Task metadata not found in history",
                    preparation_needed=[
                        "Call set_coding_task first to create the task"
                    ],
                    guidance="You must call set_coding_task before calling judge_testing_implementation. The task_id must come from a successful set_coding_task call.",
                ),
            )

        # Early validation: require credible test evidence
        missing_evidence: list[str] = []
        if not test_files:
            missing_evidence.append("List the test files created/modified")

        # Use LLM-based validation for test output
        test_output_valid = await validate_test_output(
            test_execution_results or "",
            ctx,
            context="Validating test execution output for judge_testing_implementation",
        )
        if not test_output_valid:
            missing_evidence.append(
                "Provide raw test runner output including pass/fail summary"
            )

        if missing_evidence:
            # Minimal metadata if not loaded yet
            minimal_metadata = task_metadata or TaskMetadata(
                title="Testing Validation",
                description="Insufficient test evidence provided",
                user_requirements="",
                state=TaskState.TESTING,
                task_size=TaskSize.M,
            )
            guidance = WorkflowGuidance(
                next_tool="judge_testing_implementation",
                reasoning="Testing validation requires raw runner output and listed test files",
                preparation_needed=[
                    "Run the test suite (e.g., pytest -q, npm test, go test)",
                    "Copy/paste the raw test output with the summary",
                    "List test file paths",
                    "Include coverage summary if available",
                ],
                guidance=(
                    "Please rerun tests and provide the raw output (not a narrative). "
                    "Include pass/fail counts and list the test files modified."
                ),
            )
            return JudgeResponse(
                approved=False,
                required_improvements=missing_evidence,
                feedback="Insufficient evidence to validate testing results.",
                current_task_metadata=minimal_metadata,
                workflow_guidance=guidance,
            )

        # Track test files in task metadata
        for test_file in test_files:
            task_metadata.add_test_file(test_file)

        # Update test types status
        if test_types_implemented:
            for test_type in test_types_implemented:
                # Determine status based on execution results
                if (
                    "failed" in test_execution_results.lower()
                    or "error" in test_execution_results.lower()
                ):
                    status = "failing"
                elif (
                    "passed" in test_execution_results.lower()
                    or "success" in test_execution_results.lower()
                ):
                    status = "passing"
                else:
                    status = "unknown"
                task_metadata.update_test_status(test_type, status)

        test_coverage = task_metadata.get_test_coverage_summary()
        logger.debug(f"Test coverage summary: {test_coverage}")

        # COMPREHENSIVE TESTING EVALUATION using LLM
        user_requirements = task_metadata.user_requirements

        # Load conversation history for context
        conversation_history = (
            await conversation_service.load_filtered_context_for_enrichment(
                task_id, "", ctx
            )
        )
        history_json_array = [
            {
                "timestamp": entry.timestamp,  # Already epoch int
                "tool": entry.source,
                "input": entry.input,
                "output": entry.output,
            }
            for entry in conversation_history[-10:]  # Last 10 entries for context
        ]

        # Prepare comprehensive test evaluation using LLM
        from mcp_as_a_judge.models import (
            SystemVars,
            TestingEvaluationUserVars,
        )
        from mcp_as_a_judge.prompting.loader import create_separate_messages

        # Create system and user variables for testing evaluation
        system_vars = SystemVars(
            response_schema=json.dumps(JudgeResponse.model_json_schema()),
            max_tokens=MAX_TOKENS,
        )
        user_vars = TestingEvaluationUserVars(
            user_requirements=user_requirements,
            task_description=task_metadata.description,
            modified_files=task_metadata.modified_files,
            test_summary=test_summary,
            test_files=test_files,
            test_execution_results=test_execution_results,
            test_coverage_report=test_coverage_report
            if test_coverage_report
            else "No coverage report provided",
            test_types_implemented=test_types_implemented
            if test_types_implemented
            else [],
            testing_framework=testing_framework
            if testing_framework
            else "Not specified",
            performance_test_results=performance_test_results
            if performance_test_results
            else "No performance tests",
            manual_test_notes=manual_test_notes
            if manual_test_notes
            else "No manual testing notes",
            conversation_history=history_json_array,
        )

        # Create messages for comprehensive testing evaluation
        messages = create_separate_messages(
            "system/judge_testing_implementation.md",
            "user/judge_testing_implementation.md",
            system_vars,
            user_vars,
        )

        # Use LLM for comprehensive testing evaluation
        response_text = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=MAX_TOKENS,
            prefer_sampling=True,
        )

        # Parse the comprehensive evaluation response
        try:
            json_content = extract_json_from_response(response_text)
            testing_evaluation = JudgeResponse.model_validate_json(json_content)

            testing_approved = testing_evaluation.approved
            required_improvements = testing_evaluation.required_improvements
            evaluation_feedback = testing_evaluation.feedback

        except (ValidationError, ValueError) as e:
            # Fallback to basic evaluation if LLM fails
            logger.warning(
                f"LLM testing evaluation failed, using basic validation: {e}"
            )

            # Basic validation as fallback
            has_adequate_tests = len(test_files) > 0
            tests_passing = (
                "passed" in test_execution_results.lower()
                and "failed" not in test_execution_results.lower()
            )
            no_warnings = "warning" not in test_execution_results.lower()
            no_failures = (
                "failed" not in test_execution_results.lower()
                and "error" not in test_execution_results.lower()
            )
            has_coverage = test_coverage_report and test_coverage_report.strip() != ""

            testing_approved = (
                has_adequate_tests and tests_passing and no_warnings and no_failures
            )

            required_improvements = []
            if not has_adequate_tests:
                required_improvements.append("No test files provided")
            if not tests_passing:
                required_improvements.append("Tests are not passing")
            if not no_warnings:
                required_improvements.append(
                    "Test execution contains warnings that need to be addressed"
                )
            if not no_failures:
                required_improvements.append(
                    "Test execution contains failures or errors"
                )
            if not has_coverage and len(test_files) > 0:
                required_improvements.append(
                    "Test coverage report not provided - coverage analysis recommended"
                )

            evaluation_feedback = (
                "Basic validation performed due to LLM evaluation failure"
            )

        if testing_approved:
            # Mark testing as approved for completion validation
            task_metadata.mark_testing_approved()

            # Keep task state as TESTING - final completion will transition to COMPLETED
            # The workflow will guide to judge_coding_task_completion next

            # Use LLM evaluation feedback if available, otherwise create basic feedback
            if "evaluation_feedback" in locals():
                feedback = f"""✅ **TESTING IMPLEMENTATION APPROVED**

{evaluation_feedback}

**Test Summary:** {test_summary}

**Test Files ({len(test_files)}):**
{chr(10).join(f"- {file}" for file in test_files)}

**Test Execution:** {test_execution_results}

**Test Types:** {", ".join(test_types_implemented) if test_types_implemented else "Not specified"}

**Testing Framework:** {testing_framework if testing_framework else "Not specified"}

**Coverage:** {test_coverage_report if test_coverage_report else "Not provided"}

✅ **Ready for final task completion review.**"""
            else:
                feedback = f"""✅ **TESTING IMPLEMENTATION APPROVED**

**Test Summary:** {test_summary}

**Test Files ({len(test_files)}):**
{chr(10).join(f"- {file}" for file in test_files)}

**Test Execution:** {test_execution_results}

**Assessment:** The testing implementation meets the requirements. All tests are passing and provide adequate coverage for the implemented functionality.

✅ **Ready for final task completion review.**"""

        else:
            # Use LLM evaluation feedback if available, otherwise create basic feedback
            if "evaluation_feedback" in locals():
                feedback = f"""❌ **TESTING IMPLEMENTATION NEEDS IMPROVEMENT**

{evaluation_feedback}

**Test Summary:** {test_summary}

**Test Execution Results:** {test_execution_results}

📋 **Please address these testing issues before proceeding to task completion.**"""
            else:
                feedback = f"""❌ **TESTING IMPLEMENTATION NEEDS IMPROVEMENT**

**Test Summary:** {test_summary}

**Issues Found:**
{chr(10).join(f"- {issue}" for issue in required_improvements)}

**Test Execution Results:** {test_execution_results}

**Required Actions:**
- Write comprehensive tests for all implemented functionality
- Ensure all tests pass successfully
- Provide test coverage analysis
- Follow testing best practices for the framework

📋 **Please address these testing issues before proceeding to task completion.**"""

        # Calculate workflow guidance
        workflow_guidance = await calculate_next_stage(
            task_metadata=task_metadata,
            current_operation="judge_testing_implementation_completed",
            conversation_service=conversation_service,
            ctx=ctx,
        )

        # Create enhanced response
        result = JudgeResponse(
            approved=testing_approved,
            required_improvements=required_improvements,
            feedback=feedback,
            current_task_metadata=task_metadata,
            workflow_guidance=workflow_guidance,
        )

        # Save tool interaction to conversation history
        await conversation_service.save_tool_interaction_and_cleanup(
            session_id=task_id,  # Use task_id as primary key
            tool_name="judge_testing_implementation",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(
                result.model_dump(
                    mode="json",
                    exclude_unset=True,
                    exclude_none=True,
                    exclude_defaults=True,
                )
            ),
        )

        return result

    except Exception as e:
        import traceback

        error_details = f"Error during testing validation: {e!s}\nTraceback: {traceback.format_exc()}"

        # Create error guidance
        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred during testing validation",
            preparation_needed=["Review error details", "Check task parameters"],
            guidance=f"Error during testing validation: {e!s}. Please review and try again.",
        )

        # Create minimal task metadata for error case
        if "task_metadata" in locals() and task_metadata is not None:
            error_metadata = task_metadata
        else:
            error_metadata = TaskMetadata(
                title="Error Task",
                description="Error occurred during testing validation",
                user_requirements="Error occurred before task metadata could be loaded",
                state=TaskState.TESTING,
                task_size=TaskSize.M,
                tags=["error"],
            )

        # For all errors, return enhanced error response
        error_result = JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during testing validation"],
            feedback=error_details,
            current_task_metadata=error_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction_and_cleanup(
                session_id=task_id if "task_id" in locals() else "unknown",
                tool_name="judge_testing_implementation",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(
                    error_result.model_dump(
                        mode="json",
                        exclude_unset=True,
                        exclude_none=True,
                        exclude_defaults=True,
                    )
                ),
            )

        return error_result


def main() -> None:
    """Entry point for the MCP as a Judge server."""
    # Option to suppress stderr output to avoid client-side prefixes
    # Uncomment the following lines to redirect stderr to /dev/null (Unix) or NUL (Windows)
    # import os
    # import sys
    # if os.getenv("SUPPRESS_STDERR", "false").lower() == "true":
    #     if os.name == 'nt':  # Windows
    #         sys.stderr = open('NUL', 'w')
    #     else:  # Unix/Linux/macOS
    #         sys.stderr = open('/dev/null', 'w')

    # FastMCP servers use mcp.run() directly with stdio transport for MCP clients
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

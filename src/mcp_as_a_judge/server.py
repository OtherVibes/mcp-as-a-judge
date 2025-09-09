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

from mcp_as_a_judge.coding_task_manager import (
    create_new_coding_task,
    save_task_metadata_to_history,
    update_existing_coding_task,
)
from mcp_as_a_judge.constants import MAX_TOKENS
from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.db.db_config import load_config
from mcp_as_a_judge.elicitation_provider import elicitation_provider
from mcp_as_a_judge.logging_config import (
    get_logger,
    log_startup_message,
    log_tool_execution,
    setup_logging,
)
from mcp_as_a_judge.messaging.llm_provider import llm_provider
from mcp_as_a_judge.models import (
    JudgeCodeChangeSystemVars,
    JudgeCodeChangeUserVars,
    JudgeCodingPlanSystemVars,
    JudgeCodingPlanUserVars,
    JudgeResponse,
    ResearchValidationResponse,
    ResearchValidationSystemVars,
    ResearchValidationUserVars,
    WorkflowGuidance,
)
from mcp_as_a_judge.models.enhanced_responses import (
    EnhancedResponseFactory,
    MissingRequirementsResult,
    ObstacleResult,
    TaskAnalysisResult,
    TaskCompletionResult,
)
from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskState, ResearchScope
from mcp_as_a_judge.prompt_loader import create_separate_messages
from mcp_as_a_judge.server_helpers import (
    extract_json_from_response,
    generate_dynamic_elicitation_model,
    generate_validation_error_message,
    initialize_llm_configuration,
)
from mcp_as_a_judge.tool_description_provider import (
    tool_description_provider,
)
from mcp_as_a_judge.workflow import calculate_next_stage

setup_logging()
mcp = FastMCP(name="MCP-as-a-Judge")
initialize_llm_configuration()

config = load_config()
conversation_service = ConversationHistoryService(config)
log_startup_message(config)
logger = get_logger(__name__)



@mcp.tool(description=tool_description_provider.get_description("set_coding_task"))  # type: ignore[misc,unused-ignore]
async def set_coding_task(
    user_request: str,
    task_title: str,
    task_description: str,
    ctx: Context,

    # FOR UPDATING EXISTING TASKS ONLY
    task_id: str | None = None,  # REQUIRED when updating existing task
    user_requirements: str | None = None,  # Updates current requirements

    # OPTIONAL
    tags: list[str] | None = None,
) -> TaskAnalysisResult:
    """Create or update coding task metadata with enhanced workflow management."""
    task_id_for_logging = task_id or "new_task"

    # Log tool execution start
    log_tool_execution("set_coding_task", task_id_for_logging)

    original_input = {
        "user_request": user_request,
        "task_title": task_title,
        "task_description": task_description,
        "task_id": task_id,
        "user_requirements": user_requirements,
        "tags": tags,
    }

    try:
        if task_id:
            task_metadata = await update_existing_coding_task(
                task_id=task_id,
                user_request=user_request,
                task_title=task_title,
                task_description=task_description,
                user_requirements=user_requirements,
                state=None,  # State updates not allowed via set_coding_task
                tags=tags or [],
                conversation_service=conversation_service,
            )
            action = "updated"
            context_summary = f"Updated coding task '{task_metadata.title}' (ID: {task_metadata.task_id})"

        else:
            task_metadata = await create_new_coding_task(
                user_request=user_request,
                task_title=task_title,
                task_description=task_description,
                user_requirements=user_requirements or "",
                tags=tags or [],
                conversation_service=conversation_service,
            )
            action = "created"
            context_summary = f"Created new coding task '{task_metadata.title}' (ID: {task_metadata.task_id})"
        workflow_guidance = await calculate_next_stage(
            task_metadata=task_metadata,
            current_operation=f"set_coding_task_{action}",
            conversation_service=conversation_service,
            ctx=ctx,
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

        await conversation_service.save_tool_interaction(
            session_id=task_metadata.task_id,
            tool_name="set_coding_task",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(result.model_dump(mode='json')),
        )

        return result

    except Exception as e:
        # Create error response
        error_metadata = TaskMetadata(
            title=task_title,
            description=task_description,
            user_requirements=user_requirements or "",
            state=TaskState.CREATED,
            tags=tags or [],
        )

        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred during task creation/update",
            preparation_needed=["Review error details", "Check task parameters"],
            guidance=f"Error occurred: {e!s}. Please review task parameters and try again."
        )

        error_result = EnhancedResponseFactory.create_task_analysis_result(
            action="error",
            context_summary=f"Error creating/updating task: {e!s}",
            current_task_metadata=error_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction (use task_id if available, otherwise generate one for logging)
        error_task_id = task_id or error_metadata.task_id
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=error_task_id,
                tool_name="set_coding_task",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump(mode='json')),
            )

        return error_result


@mcp.tool(description=tool_description_provider.get_description("raise_obstacle"))  # type: ignore[misc,unused-ignore]
async def raise_obstacle(
    problem: str,
    research: str,
    options: list[str],
    task_id: str,  # REQUIRED: Task ID for context and memory
    ctx: Context,
) -> ObstacleResult:
    """Obstacle handling tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("raise_obstacle", task_id)

    # Store original input for saving later
    original_input = {
        "problem": problem,
        "research": research,
        "options": options,
        "task_id": task_id,
    }

    try:
        # Load task metadata to get current context
        from mcp_as_a_judge.coding_task_manager import load_task_metadata_from_history

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        if not task_metadata:
            # Create minimal task metadata for obstacle handling
            task_metadata = TaskMetadata(
                name="obstacle-handling",
                title="Obstacle Resolution",
                description=f"Handling obstacle: {problem}",
                user_requirements="Resolve obstacle to continue task",
                state=TaskState.BLOCKED,
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
        information_needed = "User needs to choose from available options and provide any additional context"
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
                preparation_needed=["Review the obstacle resolution", "Update task requirements if needed"],
                guidance="Call set_coding_task to update the task with any new requirements or clarifications from the obstacle resolution. Then continue with the workflow."
            )

            # Create enhanced response
            result = ObstacleResult(
                obstacle_acknowledged=True,
                resolution_guidance=f"✅ OBSTACLE RESOLVED: {response_text}",
                alternative_approaches=options,
                current_task_metadata=task_metadata,
                workflow_guidance=workflow_guidance,
            )

            # Save successful interaction as conversation record
            await conversation_service.save_tool_interaction(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(result.model_dump(mode='json')),
            )

            return result

        else:
            # Elicitation failed or not available - return the fallback message
            workflow_guidance = WorkflowGuidance(
                next_tool=None,
                reasoning="Obstacle elicitation failed or unavailable",
                preparation_needed=["Manual intervention required"],
                guidance=f"Obstacle not resolved: {elicit_result.message}. Manual intervention required."
            )

            result = ObstacleResult(
                obstacle_acknowledged=False,
                resolution_guidance=elicit_result.message,
                alternative_approaches=options,
                current_task_metadata=task_metadata,
                workflow_guidance=workflow_guidance,
            )

            # Save failed interaction
            await conversation_service.save_tool_interaction(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(result.model_dump(mode='json')),
            )

            return result

    except Exception as e:
        # Create error response
        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred while handling obstacle",
            preparation_needed=["Review error details", "Manual intervention required"],
            guidance=f"Error handling obstacle: {e!s}. Manual intervention required."
        )

        error_result = ObstacleResult(
            obstacle_acknowledged=False,
            resolution_guidance=f"❌ ERROR: Failed to elicit user decision. Error: {e!s}. Cannot resolve obstacle without user input.",
            alternative_approaches=options,
            current_task_metadata=task_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump(mode='json')),
            )

        return error_result


@mcp.tool(
    description=tool_description_provider.get_description("raise_missing_requirements")
)  # type: ignore[misc,unused-ignore]
async def raise_missing_requirements(
    current_request: str,
    identified_gaps: list[str],
    specific_questions: list[str],
    task_id: str,  # REQUIRED: Task ID for context and memory
    ctx: Context,
) -> MissingRequirementsResult:
    """Requirements clarification tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("raise_missing_requirements", task_id)

    # Store original input for saving later
    original_input = {
        "current_request": current_request,
        "identified_gaps": identified_gaps,
        "specific_questions": specific_questions,
        "task_id": task_id,
    }

    try:
        # Load task metadata to get current context
        from mcp_as_a_judge.coding_task_manager import load_task_metadata_from_history

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        if not task_metadata:
            # Create minimal task metadata for requirements clarification
            task_metadata = TaskMetadata(
                name="requirements-clarification",
                title="Requirements Clarification",
                description=f"Clarifying requirements: {current_request}",
                user_requirements=current_request,
                state=TaskState.CREATED,
                tags=["requirements"],
            )

        # Format the gaps and questions for clarity
        formatted_gaps = "\n".join(f"• {gap}" for gap in identified_gaps)
        formatted_questions = "\n".join(
            f"{i + 1}. {question}" for i, question in enumerate(specific_questions)
        )

        context_info = "Agent needs clarification on user requirements to proceed with implementation"
        information_needed = (
            "Clarified requirements, answers to specific questions, and priority levels"
        )
        current_understanding = f"Current request: {current_request}. Gaps: {formatted_gaps}. Questions: {formatted_questions}"

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
            clarified_requirements = f"{current_request}\n\nClarifications: {response_text}"
            task_metadata.update_requirements(clarified_requirements, source="clarification")

            # HITL tools should always direct to set_coding_task to update requirements
            workflow_guidance = WorkflowGuidance(
                next_tool="set_coding_task",
                reasoning="Requirements clarified through user interaction. Task requirements have been updated and need to be processed.",
                preparation_needed=["Review the clarified requirements", "Update task metadata with new information"],
                guidance="Call set_coding_task to update the task with the clarified requirements. The task requirements have been updated with user clarifications and the workflow can continue."
            )

            # Create enhanced response
            result = MissingRequirementsResult(
                clarification_needed=False,
                missing_information=[],  # No longer missing
                clarification_questions=[],  # All answered
                current_task_metadata=task_metadata,
                workflow_guidance=workflow_guidance,
            )

            # Save successful interaction
            await conversation_service.save_tool_interaction(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(result.model_dump(mode='json')),
            )

            return result

        else:
            # Elicitation failed or not available - return the fallback message
            workflow_guidance = WorkflowGuidance(
                next_tool=None,
                reasoning="Requirements clarification failed or unavailable",
                preparation_needed=["Manual intervention required"],
                guidance=f"Requirements clarification failed: {elicit_result.message}. Manual intervention required."
            )

            result = MissingRequirementsResult(
                clarification_needed=True,
                missing_information=identified_gaps,
                clarification_questions=specific_questions,
                current_task_metadata=task_metadata,
                workflow_guidance=workflow_guidance,
            )

            # Save failed interaction
            await conversation_service.save_tool_interaction(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(result.model_dump(mode='json')),
            )

            return result

    except Exception as e:
        # Create error response
        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred while clarifying requirements",
            preparation_needed=["Review error details", "Manual intervention required"],
            guidance=f"Error clarifying requirements: {e!s}. Manual intervention required."
        )

        error_result = MissingRequirementsResult(
            clarification_needed=True,
            missing_information=identified_gaps,
            clarification_questions=specific_questions,
            current_task_metadata=task_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=task_id,  # Use task_id as primary key
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump(mode='json')),
            )

        return error_result


@mcp.tool(description=tool_description_provider.get_description("judge_coding_task_completion"))  # type: ignore[misc,unused-ignore]
async def judge_coding_task_completion(
    task_id: str,  # REQUIRED: Task ID for context and validation
    completion_summary: str,
    requirements_met: list[str],
    implementation_details: str,
    ctx: Context,

    # OPTIONAL
    remaining_work: list[str] | None = None,
    quality_notes: str | None = None,
    testing_status: str | None = None,
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
        from mcp_as_a_judge.coding_task_manager import load_task_metadata_from_history

        logger.info(f"🔍 judge_coding_task_completion: Loading task metadata for task_id: {task_id}")

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        logger.info(f"🔍 judge_coding_task_completion: Task metadata loaded: {task_metadata is not None}")
        if task_metadata:
            logger.info(f"🔍 judge_coding_task_completion: Task state: {task_metadata.state}, title: {task_metadata.title}")
        else:
            conversation_history = await conversation_service.get_conversation_history(task_id)
            logger.info(f"🔍 judge_coding_task_completion: Conversation history entries: {len(conversation_history)}")
            for entry in conversation_history[-5:]:
                logger.info(f"🔍 judge_coding_task_completion: History entry: {entry.source} at {entry.timestamp}")

        if not task_metadata:
            # Create a minimal task metadata for debugging
            task_metadata = TaskMetadata(
                task_id=task_id,
                name="unknown-task",
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements="Task requirements not found",
                state=TaskState.COMPLETED,  # Appropriate state for completion check
                tags=["debug", "missing-metadata"],
            )

            # Return debug information
            return TaskCompletionResult(
                approved=False,
                feedback=f"Task {task_id} not found in conversation history. This usually means set_coding_task was not called first, or the server was restarted and lost the in-memory data.",
                current_task_metadata=task_metadata,
                workflow_guidance=WorkflowGuidance(
                    next_tool="set_coding_task",
                    reasoning="Task metadata not found in history",
                    preparation_needed=["Call set_coding_task first to create the task"],
                    guidance="You must call set_coding_task before calling judge_coding_task_completion. The task_id must come from a successful set_coding_task call."
                ),
            )

        # Check if all requirements are met
        has_remaining_work = remaining_work and len(remaining_work) > 0
        requirements_coverage = len(requirements_met) > 0

        # Determine if task is complete
        task_complete = (
            requirements_coverage and
            not has_remaining_work and
            completion_summary.strip() != ""
        )

        if task_complete:
            # Task is complete - update state to COMPLETED
            task_metadata.update_state(TaskState.COMPLETED)

            feedback = f"""✅ TASK COMPLETION APPROVED

**Completion Summary:** {completion_summary}

**Requirements Satisfied:**
{chr(10).join(f"• {req}" for req in requirements_met)}

**Implementation Details:** {implementation_details}"""

            if quality_notes:
                feedback += f"\n\n**Quality Notes:** {quality_notes}"

            if testing_status:
                feedback += f"\n\n**Testing Status:** {testing_status}"

            feedback += "\n\n🎉 **Task successfully completed!**"

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

            if has_remaining_work:
                feedback += f"\n\n**Remaining Work:**\n{chr(10).join(f'• {work}' for work in remaining_work)}"
                required_improvements.extend(remaining_work)

            if not requirements_coverage:
                feedback += "\n\n**Issue:** No requirements marked as satisfied"
                required_improvements.append("Specify which requirements have been met")

            if not completion_summary.strip():
                feedback += "\n\n**Issue:** No completion summary provided"
                required_improvements.append("Provide a detailed completion summary")

            feedback += "\n\n📋 **Please complete the remaining work before resubmitting for final approval.**"

            workflow_guidance = await calculate_next_stage(
                task_metadata=task_metadata,
                current_operation="judge_coding_task_completion_incomplete",
                conversation_service=conversation_service,
                ctx=ctx,
            )

            result = TaskCompletionResult(
                approved=False,
                feedback=feedback,
                required_improvements=required_improvements,
                current_task_metadata=task_metadata,
                workflow_guidance=workflow_guidance,
            )

        # Save successful interaction
        await conversation_service.save_tool_interaction(
            session_id=task_id,  # Use task_id as primary key
            tool_name="judge_coding_task_completion",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(result.model_dump(mode='json')),
        )

        return result

    except Exception as e:
        # Create error response
        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred while validating task completion",
            preparation_needed=["Review error details", "Check task parameters"],
            guidance=f"Error validating task completion: {e!s}. Please review and try again."
        )

        # Create minimal task metadata for error case
        if 'task_metadata' in locals() and task_metadata is not None:
            error_metadata = task_metadata
        else:
            error_metadata = TaskMetadata(
                task_id=task_id if 'task_id' in locals() else "unknown",
                name="error-task",
                title="Error Task",
                description="Error occurred during completion validation",
                user_requirements="Error occurred before task metadata could be loaded",
                state=TaskState.IMPLEMENTING,
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
            await conversation_service.save_tool_interaction(
                session_id=task_id,
                tool_name="judge_coding_task_completion",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump(mode='json')),
            )

        return error_result





async def _validate_research_quality(
    research: str,
    research_urls: list[str],
    plan: str,
    design: str,
    user_requirements: str,
    ctx: Context,
) -> dict | None:
    """Validate research quality using AI evaluation.

    Returns:
        dict with basic judge fields if research is insufficient, None if research is adequate
    """
    # Create system and user messages for research validation
    system_vars = ResearchValidationSystemVars(
        response_schema=json.dumps(ResearchValidationResponse.model_json_schema())
    )
    user_vars = ResearchValidationUserVars(
        user_requirements=user_requirements,
        plan=plan,
        design=design,
        research=research,
        research_urls=research_urls,
        context="",  # No additional context for research validation
        conversation_history=[],  # No conversation history for research validation
    )
    messages = create_separate_messages(
        "system/research_validation.md",
        "user/research_validation.md",
        system_vars,
        user_vars,
    )

    research_response_text = await llm_provider.send_message(
        messages=messages, ctx=ctx, max_tokens=MAX_TOKENS, prefer_sampling=True
    )

    try:
        json_content = extract_json_from_response(research_response_text)
        research_validation = ResearchValidationResponse.model_validate_json(
            json_content
        )

        if (
            not research_validation.research_adequate
            or not research_validation.design_based_on_research
        ):
            validation_issue = f"Research validation failed: {research_validation.feedback}. Issues: {', '.join(research_validation.issues)}"
            context_info = f"User requirements: {user_requirements}. Research URLs: {research_urls}"

            descriptive_feedback = await generate_validation_error_message(
                validation_issue, context_info, ctx
            )

            # Return a simple dict instead of JudgeResponse to avoid validation issues
            return {
                "approved": False,
                "required_improvements": research_validation.issues,
                "feedback": descriptive_feedback,
            }

    except (ValidationError, ValueError) as e:
        raise ValueError(
            f"Failed to parse research validation response: {e}. Raw response: {research_response_text}"
        ) from e

    return None


async def _evaluate_coding_plan(
    plan: str,
    design: str,
    research: str,
    research_urls: list[str],
    user_requirements: str,
    context: str,
    conversation_history: list[dict],
    task_metadata: TaskMetadata,
    ctx: Context,
) -> JudgeResponse:
    """Evaluate coding plan using AI judge.

    Returns:
        JudgeResponse with evaluation results
    """
    # Create system and user messages from templates
    system_vars = JudgeCodingPlanSystemVars(
        response_schema=json.dumps(JudgeResponse.model_json_schema())
    )
    user_vars = JudgeCodingPlanUserVars(
        user_requirements=user_requirements,
        plan=plan,
        design=design,
        research=research,
        research_urls=research_urls,
        context=context,  # Additional context (separate from conversation history)
        conversation_history=conversation_history,  # JSON array with timestamps

        # Conditional research fields - LLM will determine these during evaluation
        research_required=task_metadata.research_required if task_metadata.research_required is not None else False,
        research_scope=task_metadata.research_scope.value if task_metadata.research_scope else "none",
        research_rationale=task_metadata.research_rationale or "",

        # Conditional internal research fields - LLM will determine these during evaluation
        internal_research_required=task_metadata.internal_research_required if task_metadata.internal_research_required is not None else False,
        related_code_snippets=task_metadata.related_code_snippets or [],

        # Conditional risk assessment fields - LLM will determine these during evaluation
        risk_assessment_required=task_metadata.risk_assessment_required if task_metadata.risk_assessment_required is not None else False,
        identified_risks=task_metadata.identified_risks or [],
        risk_mitigation_strategies=task_metadata.risk_mitigation_strategies or [],
    )
    messages = create_separate_messages(
        "system/judge_coding_plan.md",
        "user/judge_coding_plan.md",
        system_vars,
        user_vars,
    )

    response_text = await llm_provider.send_message(
        messages=messages,
        ctx=ctx,
        max_tokens=MAX_TOKENS,
        prefer_sampling=True,
    )

    # Parse the JSON response
    try:
        json_content = extract_json_from_response(response_text)
        return JudgeResponse.model_validate_json(json_content)
    except (ValidationError, ValueError) as e:
        raise ValueError(
            f"Failed to parse coding plan evaluation response: {e}. Raw response: {response_text}"
        ) from e


@mcp.tool(description=tool_description_provider.get_description("judge_coding_plan"))  # type: ignore[misc,unused-ignore]
async def judge_coding_plan(
    task_id: str,  # REQUIRED: Task ID for context and validation
    plan: str,
    design: str,
    research: str,
    research_urls: list[str],
    ctx: Context,
    context: str = "",
) -> TaskAnalysisResult:
    """Coding plan evaluation tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("judge_coding_plan", task_id)

    # Store original input for saving later
    original_input = {
        "task_id": task_id,
        "plan": plan,
        "design": design,
        "research": research,
        "context": context,
        "research_urls": research_urls,
    }

    try:
        # Load task metadata to get current context and user requirements
        from mcp_as_a_judge.coding_task_manager import load_task_metadata_from_history

        logger.info(f"🔍 judge_coding_plan: Loading task metadata for task_id: {task_id}")

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        logger.info(f"🔍 judge_coding_plan: Task metadata loaded: {task_metadata is not None}")
        if task_metadata:
            logger.info(f"🔍 judge_coding_plan: Task state: {task_metadata.state}, title: {task_metadata.title}")
        else:
            conversation_history = await conversation_service.get_conversation_history(task_id)
            logger.info(f"🔍 judge_coding_plan: Conversation history entries: {len(conversation_history)}")
            for entry in conversation_history[-5:]:
                logger.info(f"🔍 judge_coding_plan: History entry: {entry.source} at {entry.timestamp}")

        if not task_metadata:
            # Create a minimal task metadata for debugging
            task_metadata = TaskMetadata(
                task_id=task_id,
                name="unknown-task",
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements="Task requirements not found",
                state=TaskState.CREATED,
                tags=["debug", "missing-metadata"],
            )

            # Return debug information
            return TaskAnalysisResult(
                action="task_not_found",
                context_summary=f"Task {task_id} not found in conversation history. This usually means set_coding_task was not called first.",
                current_task_metadata=task_metadata,
                workflow_guidance=WorkflowGuidance(
                    next_tool="set_coding_task",
                    reasoning="Task metadata not found in history",
                    preparation_needed=["Call set_coding_task first to create the task"],
                    guidance="You must call set_coding_task before calling judge_coding_plan. The task_id must come from a successful set_coding_task call."
                ),
            )

        # Derive user requirements from task metadata
        user_requirements = task_metadata.user_requirements

        # NOTE: Conditional research, internal analysis, and risk assessment requirements
        # are now determined dynamically by the LLM through the workflow guidance system
        # rather than using hardcoded rule-based analysis

        # CONDITIONAL RESEARCH VALIDATION - Only validate if research is actually required
        if task_metadata.research_required:
            # Check if research URLs are provided when required
            if not research_urls or len(research_urls) == 0:
                validation_issue = f"Research is required (scope: {task_metadata.research_scope}). No research URLs provided. Rationale: {task_metadata.research_rationale}"
                context_info = f"User requirements: {user_requirements}. Plan: {plan[:200]}..."

                descriptive_feedback = await generate_validation_error_message(
                    validation_issue, context_info, ctx
                )

                # Calculate workflow guidance for error case
                workflow_guidance = await calculate_next_stage(
                    task_metadata=task_metadata,
                    current_operation="judge_coding_plan_insufficient_research",
                    conversation_service=conversation_service,
                    ctx=ctx,
                )

                return TaskAnalysisResult(
                    action="validation_failed",
                    context_summary=f"Coding plan validation failed: research required but no URLs provided (scope: {task_metadata.research_scope})",
                    current_task_metadata=task_metadata,
                    workflow_guidance=workflow_guidance,
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

        else:
            # Research is optional - log but don't block
            logger.info(f"Research optional for task {task_id} (research_required={task_metadata.research_required})")
            if research_urls:
                logger.info(f"Optional research provided: {len(research_urls)} URLs")

        # STEP 1: Load conversation history and format as JSON array
        conversation_history = await conversation_service.get_conversation_history(
            task_id  # Use task_id as primary key
        )
        history_json_array = (
            conversation_service.format_conversation_history_as_json_array(
                conversation_history
            )
        )

        # STEP 4: Use helper function for main evaluation with JSON array conversation history
        evaluation_result = await _evaluate_coding_plan(
            plan,
            design,
            research,
            research_urls,
            user_requirements,
            "",  # Empty context for now - can be enhanced later
            history_json_array,
            task_metadata,  # Pass task metadata for conditional features
            ctx,
        )

        # Additional research validation if approved
        if evaluation_result.approved:
            research_validation_result = await _validate_research_quality(
                research, research_urls, plan, design, user_requirements, ctx
            )
            if research_validation_result:
                # Convert old response to enhanced response
                workflow_guidance = await calculate_next_stage(
                    task_metadata=task_metadata,
                    current_operation="judge_coding_plan_research_failed",
                    conversation_service=conversation_service,
                    ctx=ctx,
                )

                return TaskAnalysisResult(
                    action="research_validation_failed",
                    context_summary=f"Coding plan research validation failed: {len(research_validation_result['required_improvements'])} issues found",
                    current_task_metadata=task_metadata,
                    workflow_guidance=workflow_guidance,
                )

        # Use the updated task metadata from the evaluation result (includes conditional requirements)
        updated_task_metadata = evaluation_result.current_task_metadata

        # Calculate workflow guidance for successful evaluation
        workflow_guidance = await calculate_next_stage(
            task_metadata=updated_task_metadata,
            current_operation="judge_coding_plan_completed",
            conversation_service=conversation_service,
            ctx=ctx,
            validation_result=evaluation_result,
        )

        # Create enhanced response
        if evaluation_result.approved:
            action = "plan_approved"
            context_summary = f"Coding plan approved for task '{updated_task_metadata.title}'"
        else:
            action = "plan_rejected"
            context_summary = f"Coding plan rejected for task '{updated_task_metadata.title}': {len(evaluation_result.required_improvements)} improvements needed"

        result = TaskAnalysisResult(
            action=action,
            context_summary=context_summary,
            current_task_metadata=updated_task_metadata,
            workflow_guidance=workflow_guidance,
        )

        # STEP 3: Save tool interaction to conversation history
        await conversation_service.save_tool_interaction(
            session_id=task_id,  # Use task_id as primary key
            tool_name="judge_coding_plan",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(result.model_dump(mode='json')),
        )

        return result

    except Exception as e:
        import traceback

        error_details = (
            f"Error during plan review: {e!s}\nTraceback: {traceback.format_exc()}"
        )

        # Create error guidance
        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred during coding plan evaluation",
            preparation_needed=["Review error details", "Check task parameters"],
            guidance=f"Error during plan review: {e!s}. Please review and try again."
        )

        # Create minimal task metadata for error case
        if 'task_metadata' in locals() and task_metadata is not None:
            error_metadata = task_metadata
        else:
            error_metadata = TaskMetadata(
                task_id=task_id if 'task_id' in locals() else "unknown",
                name="error-task",
                title="Error Task",
                description="Error occurred during plan evaluation",
                user_requirements="Error occurred before task metadata could be loaded",
                state=TaskState.PLANNING,
                tags=["error"],
            )

        # For all errors, return enhanced error response
        error_result = TaskAnalysisResult(
            action="error_occurred",
            context_summary=f"Error during coding plan evaluation: {str(e)[:100]}...",
            current_task_metadata=error_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=task_id if 'task_id' in locals() else "unknown",
                tool_name="judge_coding_plan",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump(mode='json')),
            )

        return error_result


@mcp.tool(description=tool_description_provider.get_description("judge_code_change"))  # type: ignore[misc,unused-ignore]
async def judge_code_change(
    task_id: str,  # REQUIRED: Task ID for context and validation
    code_change: str,
    ctx: Context,
    file_path: str = "File path not specified",
    change_description: str = "Change description not provided",
) -> JudgeResponse:
    """Code change evaluation tool - description loaded from tool_description_provider."""
    # Log tool execution start
    log_tool_execution("judge_code_change", task_id)

    # Store original input for saving later
    original_input = {
        "task_id": task_id,
        "code_change": code_change,
        "file_path": file_path,
        "change_description": change_description,
    }

    try:
        # Load task metadata to get current context and user requirements
        from mcp_as_a_judge.coding_task_manager import load_task_metadata_from_history

        logger.info(f"🔍 judge_code_change: Loading task metadata for task_id: {task_id}")

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        logger.info(f"🔍 judge_code_change: Task metadata loaded: {task_metadata is not None}")
        if task_metadata:
            logger.info(f"🔍 judge_code_change: Task state: {task_metadata.state}, title: {task_metadata.title}")
        else:
            conversation_history = await conversation_service.get_conversation_history(task_id)
            logger.info(f"🔍 judge_code_change: Conversation history entries: {len(conversation_history)}")
            for entry in conversation_history[-5:]:
                logger.info(f"🔍 judge_code_change: History entry: {entry.source} at {entry.timestamp}")

        if not task_metadata:
            # Create a minimal task metadata for debugging
            task_metadata = TaskMetadata(
                task_id=task_id,
                name="unknown-task",
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements="Task requirements not found",
                state=TaskState.IMPLEMENTING,
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
                    preparation_needed=["Call set_coding_task first to create the task"],
                    guidance="You must call set_coding_task before calling judge_code_change. The task_id must come from a successful set_coding_task call."
                ),
            )

        # Derive user requirements from task metadata
        user_requirements = task_metadata.user_requirements

        # STEP 1: Load conversation history and format as JSON array
        conversation_history = await conversation_service.get_conversation_history(
            task_id  # Use task_id as primary key
        )
        history_json_array = (
            conversation_service.format_conversation_history_as_json_array(
                conversation_history
            )
        )

        # STEP 2: Create system and user messages with separate context and conversation history
        system_vars = JudgeCodeChangeSystemVars(
            response_schema=json.dumps(JudgeResponse.model_json_schema())
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

            # Track the file that was reviewed (if approved)
            if judge_result.approved and file_path != "File path not specified":
                task_metadata.add_modified_file(file_path)
                logger.info(f"📁 Added file to task tracking: {file_path}")

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

            # STEP 4: Save tool interaction to conversation history
            await conversation_service.save_tool_interaction(
                session_id=task_id,  # Use task_id as primary key
                tool_name="judge_code_change",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(result.model_dump(mode='json')),
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
            guidance=f"Error during code review: {e!s}. Please review and try again."
        )

        # Create minimal task metadata for error case
        error_metadata = task_metadata if 'task_metadata' in locals() else TaskMetadata(
            title="Error Task",
            description="Error occurred during code evaluation",
            user_requirements="",
            state=TaskState.IMPLEMENTING,
            tags=["error"],
        )

        # For all errors, return enhanced error response
        error_result = JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details,
            current_task_metadata=error_metadata,
            workflow_guidance=error_guidance,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=task_id if 'task_id' in locals() else "unknown",
                tool_name="judge_code_change",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump(mode='json')),
            )

        return error_result



@mcp.tool(description=tool_description_provider.get_description("judge_testing_implementation"))  # type: ignore[misc,unused-ignore]
async def judge_testing_implementation(
    task_id: str,  # REQUIRED: Task ID for context and validation
    test_summary: str,
    test_files: list[str],
    test_execution_results: str,
    ctx: Context,
    test_coverage_report: str | None = None,
    test_types_implemented: list[str] | None = None,
    testing_framework: str | None = None,
    performance_test_results: str | None = None,
    manual_test_notes: str | None = None,
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
        from mcp_as_a_judge.coding_task_manager import load_task_metadata_from_history

        logger.info(f"🔍 judge_testing_implementation: Loading task metadata for task_id: {task_id}")

        task_metadata = await load_task_metadata_from_history(
            task_id=task_id,
            conversation_service=conversation_service,
        )

        logger.info(f"🔍 judge_testing_implementation: Task metadata loaded: {task_metadata is not None}")
        if task_metadata:
            logger.info(f"🔍 judge_testing_implementation: Task state: {task_metadata.state}, test files: {len(task_metadata.test_files)}")

        if not task_metadata:
            # Create a minimal task metadata for debugging
            task_metadata = TaskMetadata(
                task_id=task_id,
                name="unknown-task",
                title="Unknown Task",
                description="Task metadata could not be loaded from history",
                user_requirements="Task requirements not found",
                state=TaskState.TESTING,
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
                    preparation_needed=["Call set_coding_task first to create the task"],
                    guidance="You must call set_coding_task before calling judge_testing_implementation. The task_id must come from a successful set_coding_task call."
                ),
            )

        # Track test files in task metadata
        for test_file in test_files:
            task_metadata.add_test_file(test_file)

        # Update test types status
        if test_types_implemented:
            for test_type in test_types_implemented:
                # Determine status based on execution results
                if "failed" in test_execution_results.lower() or "error" in test_execution_results.lower():
                    status = "failing"
                elif "passed" in test_execution_results.lower() or "success" in test_execution_results.lower():
                    status = "passing"
                else:
                    status = "unknown"
                task_metadata.update_test_status(test_type, status)

        test_coverage = task_metadata.get_test_coverage_summary()

        # COMPREHENSIVE TESTING EVALUATION using LLM
        user_requirements = task_metadata.user_requirements

        # Load conversation history for context
        conversation_history = await conversation_service.get_conversation_history(task_id)
        history_json_array = [
            {
                "timestamp": entry.timestamp,  # Already epoch int
                "tool": entry.source,
                "input": entry.input,
                "output": entry.output
            }
            for entry in conversation_history[-10:]  # Last 10 entries for context
        ]

        # Prepare comprehensive test evaluation using LLM
        from mcp_as_a_judge.models import (
            TestingEvaluationSystemVars,
            TestingEvaluationUserVars,
        )
        from mcp_as_a_judge.prompt_loader import create_separate_messages

        # Create system and user variables for testing evaluation
        system_vars = TestingEvaluationSystemVars(
            response_schema=json.dumps(JudgeResponse.model_json_schema())
        )
        user_vars = TestingEvaluationUserVars(
            user_requirements=user_requirements,
            task_description=task_metadata.description,
            modified_files=task_metadata.modified_files,
            test_summary=test_summary,
            test_files=test_files,
            test_execution_results=test_execution_results,
            test_coverage_report=test_coverage_report or "No coverage report provided",
            test_types_implemented=test_types_implemented or [],
            testing_framework=testing_framework or "Not specified",
            performance_test_results=performance_test_results or "No performance tests",
            manual_test_notes=manual_test_notes or "No manual testing notes",
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
            logger.warning(f"LLM testing evaluation failed, using basic validation: {e}")

            # Basic validation as fallback
            has_adequate_tests = len(test_files) > 0
            tests_passing = "passed" in test_execution_results.lower() and "failed" not in test_execution_results.lower()
            no_warnings = "warning" not in test_execution_results.lower()
            no_failures = "failed" not in test_execution_results.lower() and "error" not in test_execution_results.lower()
            has_coverage = test_coverage_report is not None and test_coverage_report.strip() != ""

            testing_approved = has_adequate_tests and tests_passing and no_warnings and no_failures

            required_improvements = []
            if not has_adequate_tests:
                required_improvements.append("No test files provided")
            if not tests_passing:
                required_improvements.append("Tests are not passing")
            if not no_warnings:
                required_improvements.append("Test execution contains warnings that need to be addressed")
            if not no_failures:
                required_improvements.append("Test execution contains failures or errors")
            if not has_coverage and len(test_files) > 0:
                required_improvements.append("Test coverage report not provided - coverage analysis recommended")

            evaluation_feedback = "Basic validation performed due to LLM evaluation failure"

        if testing_approved:
            # Update task state to REVIEW_READY if tests are passing
            if task_metadata.state == TaskState.TESTING:
                task_metadata.update_state(TaskState.REVIEW_READY)

            # Use LLM evaluation feedback if available, otherwise create basic feedback
            if 'evaluation_feedback' in locals():
                feedback = f"""✅ **TESTING IMPLEMENTATION APPROVED**

{evaluation_feedback}

**Test Summary:** {test_summary}

**Test Files ({len(test_files)}):**
{chr(10).join(f"- {file}" for file in test_files)}

**Test Execution:** {test_execution_results}

**Test Types:** {', '.join(test_types_implemented) if test_types_implemented else 'Not specified'}

**Testing Framework:** {testing_framework or 'Not specified'}

**Coverage:** {test_coverage_report or 'Not provided'}

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
            if 'evaluation_feedback' in locals():
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
        await conversation_service.save_tool_interaction(
            session_id=task_id,  # Use task_id as primary key
            tool_name="judge_testing_implementation",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(result.model_dump(mode='json')),
        )

        return result

    except Exception as e:
        import traceback

        error_details = (
            f"Error during testing validation: {e!s}\nTraceback: {traceback.format_exc()}"
        )

        # Create error guidance
        error_guidance = WorkflowGuidance(
            next_tool=None,
            reasoning="Error occurred during testing validation",
            preparation_needed=["Review error details", "Check task parameters"],
            guidance=f"Error during testing validation: {e!s}. Please review and try again."
        )

        # Create minimal task metadata for error case
        if 'task_metadata' in locals() and task_metadata is not None:
            error_metadata = task_metadata
        else:
            error_metadata = TaskMetadata(
                task_id=task_id if 'task_id' in locals() else "unknown",
                name="error-task",
                title="Error Task",
                description="Error occurred during testing validation",
                user_requirements="Error occurred before task metadata could be loaded",
                state=TaskState.TESTING,
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
            await conversation_service.save_tool_interaction(
                session_id=task_id if 'task_id' in locals() else "unknown",
                tool_name="judge_testing_implementation",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump(mode='json')),
            )

        return error_result


def main() -> None:
    """Entry point for the MCP as a Judge server."""
    # FastMCP servers use mcp.run() directly with stdio transport for MCP clients
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

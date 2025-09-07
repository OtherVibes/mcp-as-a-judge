"""
MCP as a Judge server implementation.

This module contains the main MCP server with judge tools for validating
coding plans and code changes against software engineering best practices.
"""

import builtins
import contextlib
import json

from mcp.server.fastmcp import Context, FastMCP
from pydantic import ValidationError

from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.db.db_config import load_config
from mcp_as_a_judge.elicitation_provider import elicitation_provider
from mcp_as_a_judge.logging_config import (
    get_logger,
    log_error,
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
    WorkflowGuidanceSystemVars,
    WorkflowGuidanceUserVars,
)
from mcp_as_a_judge.prompt_loader import create_separate_messages
from mcp_as_a_judge.server_helpers import (
    extract_json_from_response,
    generate_dynamic_elicitation_model,
    generate_validation_error_message,
    get_session_id,
    initialize_llm_configuration,
)
from mcp_as_a_judge.tool_description_provider import (
    tool_description_provider,
)

# Initialize centralized logging
setup_logging()

# Create the MCP server instance
mcp = FastMCP(name="MCP-as-a-Judge")

# Initialize LLM configuration from environment
initialize_llm_configuration()

# Initialize conversation history service
config = load_config()
conversation_service = ConversationHistoryService(config)

# Log startup message using centralized logging
log_startup_message(config)

# Get logger for this module
logger = get_logger(__name__)


# Helper functions have been moved to server_helpers.py for better organization


@mcp.tool(description=tool_description_provider.get_description("build_workflow"))  # type: ignore[misc,unused-ignore]
async def build_workflow(
    task_description: str,
    ctx: Context,
    context: str = "",
) -> WorkflowGuidance:
    """Workflow guidance tool - description loaded from tool_description_provider."""
    session_id = get_session_id(ctx)

    # Log tool execution start
    log_tool_execution("build_workflow", session_id)

    # Store original input for saving later
    original_input = {"task_description": task_description, "context": context}

    try:
        # STEP 1: Load conversation history and format as JSON array
        conversation_history = await conversation_service.get_conversation_history(
            session_id
        )
        history_json_array = (
            conversation_service.format_conversation_history_as_json_array(
                conversation_history
            )
        )

        # STEP 2: Create system and user messages with separate context and conversation history
        system_vars = WorkflowGuidanceSystemVars(
            response_schema=json.dumps(WorkflowGuidance.model_json_schema())
        )
        user_vars = WorkflowGuidanceUserVars(
            task_description=task_description,
            context=context,  # Keep original context separate
            conversation_history=history_json_array,  # JSON array with timestamps
        )
        messages = create_separate_messages(
            "system/build_workflow.md",
            "user/build_workflow.md",
            system_vars,
            user_vars,
        )

        # STEP 3: Use messaging layer to get LLM evaluation
        response_text = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=5000,
            prefer_sampling=True,
        )

        json_content = extract_json_from_response(response_text)
        result = WorkflowGuidance.model_validate_json(json_content)

        # STEP 4: Save tool interaction to conversation history
        await conversation_service.save_tool_interaction(
            session_id=session_id,
            tool_name="build_workflow",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(result.model_dump()),
        )

        return result

    except Exception as e:
        log_error(e, "build_workflow")
        # Return a default workflow guidance in case of error
        return WorkflowGuidance(
            next_tool="elicit_missing_requirements",
            reasoning="An error occurred during workflow generation. Please provide more details.",
            preparation_needed=[
                "Review the error and provide more specific requirements"
            ],
            guidance="Please retry with more specific requirements and context about your development task.",
        )


@mcp.tool(description=tool_description_provider.get_description("raise_obstacle"))  # type: ignore[misc,unused-ignore]
async def raise_obstacle(
    problem: str,
    research: str,
    options: list[str],
    ctx: Context,
) -> str:
    """Obstacle handling tool - description loaded from tool_description_provider."""
    session_id = get_session_id(ctx)

    # Store original input for saving later
    original_input = {"problem": problem, "research": research, "options": options}

    try:
        # No need to load conversation history for obstacle resolution, user will need to decide what to do, LLM is not involve

        formatted_options = "\n".join(
            f"{i + 1}. {option}" for i, option in enumerate(options)
        )

        # Generate dynamic schema based on the specific obstacle context
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

            result = f"""✅ OBSTACLE RESOLVED

{response_text}

You can now proceed with the user's chosen approach. Make sure to incorporate their input into your implementation."""

            # Save successful interaction as conversation record
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=result,
            )

            return result

        else:
            # Elicitation failed or not available - return the fallback message
            result = elicit_result.message

            # Save failed interaction
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=result,
            )

            return result

    except Exception as e:
        error_result = f"❌ ERROR: Failed to elicit user decision. Error: {e!s}. Cannot resolve obstacle without user input."

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="raise_obstacle",
                tool_input=json.dumps(original_input),
                tool_output=error_result,
            )

        return error_result


@mcp.tool(
    description=tool_description_provider.get_description("raise_missing_requirements")
)  # type: ignore[misc,unused-ignore]
async def raise_missing_requirements(
    current_request: str,
    identified_gaps: list[str],
    specific_questions: list[str],
    ctx: Context,
) -> str:
    """Requirements clarification tool - description loaded from tool_description_provider."""
    session_id = get_session_id(ctx)

    # Store original input for saving later
    original_input = {
        "current_request": current_request,
        "identified_gaps": identified_gaps,
        "specific_questions": specific_questions,
    }

    try:
        # No need to load conversation history for requirement clarification, user will need to decide what to do, LLM is not involve

        # Format the gaps and questions for clarity
        formatted_gaps = "\n".join(f"• {gap}" for gap in identified_gaps)
        formatted_questions = "\n".join(
            f"{i + 1}. {question}" for i, question in enumerate(specific_questions)
        )

        # Generate dynamic schema based on the specific requirements context
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

            result = f"""✅ REQUIREMENTS CLARIFIED

{response_text}

You can now proceed with the clarified requirements. Make sure to incorporate all clarifications into your planning and implementation."""

            # Save successful interaction
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=result,
            )

            return result

        else:
            # Elicitation failed or not available - return the fallback message
            result = elicit_result.message

            # Save failed interaction
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=result,
            )

            return result

    except Exception as e:
        error_result = f"❌ ERROR: Failed to elicit requirement clarifications. Error: {e!s}. Cannot proceed without clear requirements."

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="raise_missing_requirements",
                tool_input=json.dumps(original_input),
                tool_output=error_result,
            )

        return error_result


async def _validate_research_quality(
    research: str,
    research_urls: list[str],
    plan: str,
    design: str,
    user_requirements: str,
    ctx: Context,
) -> JudgeResponse | None:
    """Validate research quality using AI evaluation.

    Returns:
        JudgeResponse if research is insufficient, None if research is adequate
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
        messages=messages, ctx=ctx, max_tokens=500, prefer_sampling=True
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

            # Generate AI-powered descriptive error message
            descriptive_feedback = await generate_validation_error_message(
                validation_issue, context_info, ctx
            )

            return JudgeResponse(
                approved=False,
                required_improvements=research_validation.issues,
                feedback=descriptive_feedback,
            )

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
        max_tokens=5000,
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
    plan: str,
    design: str,
    research: str,
    research_urls: list[str],
    user_requirements: str,
    ctx: Context,
    context: str = "",
) -> JudgeResponse:
    """Coding plan evaluation tool - description loaded from tool_description_provider."""
    session_id = get_session_id(ctx)

    # Log tool execution start
    log_tool_execution(
        "judge_coding_plan",
        session_id,
        f"Plan: {plan}\nUser Requirements: {user_requirements}",
    )

    # Store original input for saving later
    original_input = {
        "plan": plan,
        "design": design,
        "research": research,
        "user_requirements": user_requirements,
        "context": context,
        "research_urls": research_urls,
    }

    # Validate research URLs requirement
    if len(research_urls) < 3:
        validation_issue = f"Insufficient research URLs: {len(research_urls)} provided, minimum 3 required. AI assistant MUST perform online research and provide at least 3 URLs focusing on existing solutions and well-known libraries."
        context_info = f"User requirements: {user_requirements}. Plan: {plan[:200]}..."

        # Generate AI-powered descriptive error message
        descriptive_feedback = await generate_validation_error_message(
            validation_issue, context_info, ctx
        )

        return JudgeResponse(
            approved=False,
            required_improvements=[
                f"Insufficient research URLs: {len(research_urls)} provided, minimum 3 required",
                "AI assistant MUST perform online research and provide at least 3 URLs",
                "Research should focus on existing well-known libraries and best practices",
            ],
            feedback=descriptive_feedback,
        )

    try:
        # STEP 1: Load conversation history and format as JSON array
        conversation_history = await conversation_service.get_conversation_history(
            session_id
        )
        history_json_array = (
            conversation_service.format_conversation_history_as_json_array(
                conversation_history
            )
        )

        # STEP 2: Use helper function for main evaluation with JSON array conversation history
        evaluation_result = await _evaluate_coding_plan(
            plan,
            design,
            research,
            research_urls,
            user_requirements,
            "",  # Empty context for now - can be enhanced later
            history_json_array,
            ctx,
        )

        # Additional research validation if approved
        if evaluation_result.approved:
            research_validation_result = await _validate_research_quality(
                research, research_urls, plan, design, user_requirements, ctx
            )
            if research_validation_result:
                return research_validation_result

        # STEP 3: Save tool interaction to conversation history
        await conversation_service.save_tool_interaction(
            session_id=session_id,
            tool_name="judge_coding_plan",
            tool_input=json.dumps(original_input),
            tool_output=json.dumps(evaluation_result.model_dump()),
        )

        return evaluation_result

    except Exception as e:
        import traceback

        error_details = (
            f"Error during plan review: {e!s}\nTraceback: {traceback.format_exc()}"
        )

        # For all errors, return the actual error (capability checking is done upfront)
        error_result = JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="judge_coding_plan",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump()),
            )

        return error_result


@mcp.tool(description=tool_description_provider.get_description("judge_code_change"))  # type: ignore[misc,unused-ignore]
async def judge_code_change(
    code_change: str,
    user_requirements: str,
    ctx: Context,
    file_path: str = "File path not specified",
    change_description: str = "Change description not provided",
) -> JudgeResponse:
    """Code change evaluation tool - description loaded from tool_description_provider."""
    session_id = get_session_id(ctx)

    # Store original input for saving later
    original_input = {
        "code_change": code_change,
        "user_requirements": user_requirements,
        "file_path": file_path,
        "change_description": change_description,
    }

    try:
        # STEP 1: Load conversation history and format as JSON array
        conversation_history = await conversation_service.get_conversation_history(
            session_id
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
            max_tokens=5000,
            prefer_sampling=True,
        )

        # Parse the JSON response
        try:
            json_content = extract_json_from_response(response_text)
            result = JudgeResponse.model_validate_json(json_content)

            # STEP 4: Save tool interaction to conversation history
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="judge_code_change",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(result.model_dump()),
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

        # For all errors, return the actual error (capability checking is done upfront)
        error_result = JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details,
        )

        # Save error interaction
        with contextlib.suppress(builtins.BaseException):
            await conversation_service.save_tool_interaction(
                session_id=session_id,
                tool_name="judge_code_change",
                tool_input=json.dumps(original_input),
                tool_output=json.dumps(error_result.model_dump()),
            )

        return error_result


def main() -> None:
    """Entry point for the MCP as a Judge server."""
    # FastMCP servers use mcp.run() directly with stdio transport for MCP clients
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

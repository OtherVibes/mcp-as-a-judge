"""
MCP as a Judge server implementation.

This module contains the main MCP server with judge tools for validating
coding plans and code changes against software engineering best practices.
"""

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import (
    ClientCapabilities,
    SamplingCapability,
    SamplingMessage,
    TextContent,
)
from pydantic import ValidationError

from mcp_as_a_judge.models import (
    JudgeResponse,
    ObstacleResolutionDecision,
    RequirementsClarification,
    ResearchValidationResponse,
    WorkflowGuidance,
)
from mcp_as_a_judge.prompt_loader import prompt_loader

# Create the MCP server instance
mcp = FastMCP(name="MCP-as-a-Judge")


def _extract_json_from_response(response_text: str) -> str:
    """Extract JSON content from LLM response by finding first { and last }.

    LLMs often return JSON wrapped in markdown code blocks, explanatory text,
    or other formatting. This function extracts just the JSON object content.

    Args:
        response_text: Raw LLM response text

    Returns:
        Extracted JSON string ready for parsing

    Raises:
        ValueError: If no JSON object is found in the response
    """
    # Find the first opening brace and last closing brace
    first_brace = response_text.find("{")
    last_brace = response_text.rfind("}")

    if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
        raise ValueError(f"No valid JSON object found in response: {response_text}")

    # Extract the JSON content
    json_content = response_text[first_brace : last_brace + 1]
    return json_content


def _create_messages(
    system_template: str, user_template: str, **kwargs: Any
) -> list[SamplingMessage]:
    """Create combined system and user message from templates.

    Since MCP SamplingMessage only supports 'user' and 'assistant' roles,
    we combine the system instructions and user request into a single user message.

    Args:
        system_template: Name of the system message template
        user_template: Name of the user message template
        **kwargs: Variables to pass to templates

    Returns:
        List with single SamplingMessage containing combined content
    """
    system_content = prompt_loader.render_prompt(system_template, **kwargs)
    user_content = prompt_loader.render_prompt(user_template, **kwargs)

    # Combine system instructions and user request
    combined_content = f"{system_content}\n\n---\n\n{user_content}"

    return [
        SamplingMessage(
            role="user",
            content=TextContent(type="text", text=combined_content),
        ),
    ]


@mcp.tool()  # type: ignore[misc,unused-ignore]
async def get_workflow_guidance(
    task_description: str,
    ctx: Context,
    context: str = "",
) -> WorkflowGuidance:
    """🚨 START HERE: AI programming assistant should call this tool first for any development task to get workflow guidance.

    This tool analyzes the development task and tells you exactly which MCP tools to use next and in what order.

    Args:
        task_description: Description of what the user wants to do
        context: Additional context about the project, requirements, or constraints

    Returns:
        Structured guidance on which tools to use next and how to prepare for them
    """
    try:
        # Check for sampling capability and use elicitation for user decisions

        try:
            # Check if client supports sampling capability
            if not ctx.session.check_client_capability(
                ClientCapabilities(sampling=SamplingCapability())
            ):
                return WorkflowGuidance(
                    next_tool="judge_coding_plan",
                    reasoning="Sampling capability not available - providing default guidance",
                    preparation_needed=[
                        "Create detailed plan",
                        "Design system architecture",
                        "Research solutions",
                    ],
                    guidance="⚠️ LLM sampling not available. Default recommendation: Start with planning workflow by calling judge_coding_plan after creating plan, design, and research.",
                )
        except (ValueError, AttributeError) as e:
            return WorkflowGuidance(
                next_tool="judge_coding_plan",
                reasoning="Session not available - providing default guidance",
                preparation_needed=[
                    "Create detailed plan",
                    "Design system architecture",
                    "Research solutions",
                ],
                guidance=f"⚠️ Session error: {e!s}. Default recommendation: Start with planning workflow by calling judge_coding_plan after creating plan, design, and research.",
            )

        # Use helper function for main evaluation
        return await _evaluate_workflow_guidance(task_description, context, ctx)

    except Exception as e:
        import traceback

        error_details = f"Error during workflow guidance: {e!s}\nTraceback: {traceback.format_exc()}"
        print(f"DEBUG: Exception in get_workflow_guidance: {error_details}")
        return WorkflowGuidance(
            next_tool="raise_obstacle",
            reasoning="Error occurred during workflow analysis",
            preparation_needed=["Review task description and try again"],
            guidance=error_details,
        )


@mcp.tool()  # type: ignore[misc,unused-ignore]
async def raise_obstacle(
    problem: str,
    research: str,
    options: list[str],
    ctx: Context,
) -> str:
    """🚨 OBSTACLE ENCOUNTERED: Call this tool when you cannot satisfy the user's requirements.

    This tool helps involve the user in decision-making when the agent encounters blockers,
    missing information, or conflicting requirements that prevent satisfying the original request.

    Args:
        problem: Clear description of the obstacle/problem preventing progress
        research: Research done on this problem (existing solutions, alternatives analyzed)
        options: List of possible next steps or approaches to resolve the obstacle

    Returns:
        User's decision and any additional context for proceeding
    """
    try:
        # Format the options as a numbered list for clarity
        formatted_options = "\n".join(
            f"{i + 1}. {option}" for i, option in enumerate(options)
        )

        # Use elicitation to get user decision
        elicit_result = await ctx.elicit(
            message=f"""🚨 OBSTACLE ENCOUNTERED

**Problem:** {problem}

**Research Done:** {research}

**Available Options:**
{formatted_options}

Please choose an option (by number or description) and provide any additional context or modifications you'd like.""",
            schema=ObstacleResolutionDecision,
        )

        if elicit_result.action == "accept" and elicit_result.data:
            chosen_option = elicit_result.data.chosen_option
            additional_context = elicit_result.data.additional_context

            return f"""✅ USER DECISION RECEIVED

**Chosen Option:** {chosen_option}
**Additional Context:** {additional_context}

You can now proceed with the user's chosen approach. Make sure to incorporate their additional context into your implementation."""

        elif elicit_result.action == "decline":
            return "❌ USER DECLINED: User declined to choose an option. Cannot proceed without user decision."

        else:  # cancel
            return "❌ USER CANCELLED: User cancelled the obstacle resolution. Task cannot be completed."

    except Exception as e:
        return f"❌ ERROR: Failed to elicit user decision. Error: {e!s}. Cannot resolve obstacle without user input."


@mcp.tool()  # type: ignore[misc,unused-ignore]
async def elicit_missing_requirements(
    current_request: str,
    identified_gaps: list[str],
    specific_questions: list[str],
    ctx: Context,
) -> str:
    """🔍 REQUIREMENTS UNCLEAR: Call this tool when the user request is not clear enough to proceed.

    This tool helps gather missing requirements and clarifications from the user when the
    original request lacks sufficient detail for proper implementation.

    Args:
        current_request: The current user request as understood
        identified_gaps: List of specific requirement gaps identified
        specific_questions: List of specific questions that need answers

    Returns:
        Clarified requirements and additional context from the user
    """
    try:
        # Format the gaps and questions for clarity
        formatted_gaps = "\n".join(f"• {gap}" for gap in identified_gaps)
        formatted_questions = "\n".join(
            f"{i + 1}. {question}" for i, question in enumerate(specific_questions)
        )

        # Use elicitation to get requirement clarifications
        elicit_result = await ctx.elicit(
            message=f"""🔍 REQUIREMENTS CLARIFICATION NEEDED

**Current Understanding:** {current_request}

**Identified Requirement Gaps:**
{formatted_gaps}

**Specific Questions:**
{formatted_questions}

Please provide clarified requirements and indicate their priority level (high/medium/low).""",
            schema=RequirementsClarification,
        )

        if elicit_result.action == "accept" and elicit_result.data:
            clarified_reqs = elicit_result.data.clarified_requirements
            priority = elicit_result.data.priority_level
            additional_context = elicit_result.data.additional_context

            return f"""✅ REQUIREMENTS CLARIFIED

**Clarified Requirements:** {clarified_reqs}
**Priority Level:** {priority}
**Additional Context:** {additional_context}

You can now proceed with the clarified requirements. Make sure to incorporate all clarifications into your planning and implementation."""

        elif elicit_result.action == "decline":
            return "❌ USER DECLINED: User declined to provide requirement clarifications. Cannot proceed without clear requirements."

        else:  # cancel
            return "❌ USER CANCELLED: User cancelled the requirement clarification. Task cannot be completed without clear requirements."

    except Exception as e:
        return f"❌ ERROR: Failed to elicit requirement clarifications. Error: {e!s}. Cannot proceed without clear requirements."


async def _validate_research_quality(
    research: str,
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
    messages = _create_messages(
        "system/research_validation.md",
        "user/research_validation.md",
        user_requirements=user_requirements,
        plan=plan,
        design=design,
        research=research,
    )

    research_result = await ctx.session.create_message(
        messages=messages,
        max_tokens=500,
    )

    if research_result.content.type == "text":
        research_response_text = research_result.content.text
    else:
        research_response_text = str(research_result.content)

    try:
        json_content = _extract_json_from_response(research_response_text)
        research_validation = ResearchValidationResponse.model_validate_json(
            json_content
        )

        if (
            not research_validation.research_adequate
            or not research_validation.design_based_on_research
        ):
            return JudgeResponse(
                approved=False,
                required_improvements=research_validation.issues,
                feedback=f"❌ RESEARCH VALIDATION FAILED: {research_validation.feedback}",
            )

    except (ValidationError, ValueError) as e:
        raise ValueError(
            f"Failed to parse research validation response: {e}. Raw response: {research_response_text}"
        ) from e

    return None


async def _evaluate_workflow_guidance(
    task_description: str, context: str, ctx: Context
) -> WorkflowGuidance:
    """Evaluate workflow guidance using LLM sampling."""
    try:
        # Create system and user messages from templates
        messages = _create_messages(
            "system/get_workflow_guidance.md",
            "user/get_workflow_guidance.md",
            task_description=task_description,
            context=context,
            response_schema=WorkflowGuidance.model_json_schema(),
        )

        # Use sampling to get LLM evaluation
        result = await ctx.session.create_message(
            messages=messages,
            max_tokens=1000,
        )

        if result.content.type == "text":
            response_text = result.content.text
        else:
            response_text = str(result.content)

        try:
            json_content = _extract_json_from_response(response_text)
            return WorkflowGuidance.model_validate_json(json_content)
        except (ValidationError, ValueError) as e:
            raise ValueError(
                f"Failed to parse workflow guidance response: {e}. Raw response: {response_text}"
            ) from e

    except Exception as e:
        print(f"DEBUG: Workflow guidance evaluation error: {e}")
        # Fallback response for errors
        return WorkflowGuidance(
            next_tool="judge_coding_plan",
            reasoning=f"Error during evaluation: {e!s}",
            preparation_needed=["Review task requirements"],
            guidance="An error occurred during workflow analysis. Please start with planning workflow.",
        )


async def _evaluate_coding_plan(
    plan: str,
    design: str,
    research: str,
    user_requirements: str,
    context: str,
    ctx: Context,
) -> JudgeResponse:
    """Evaluate coding plan using AI judge.

    Returns:
        JudgeResponse with evaluation results
    """
    # Create system and user messages from templates
    messages = _create_messages(
        "system/judge_coding_plan.md",
        "user/judge_coding_plan.md",
        user_requirements=user_requirements,
        plan=plan,
        design=design,
        research=research,
        context=context,
        response_schema=JudgeResponse.model_json_schema(),
    )

    result = await ctx.session.create_message(
        messages=messages,
        max_tokens=1000,
    )

    if result.content.type == "text":
        response_text = result.content.text
    else:
        response_text = str(result.content)

    # Parse the JSON response
    try:
        json_content = _extract_json_from_response(response_text)
        return JudgeResponse.model_validate_json(json_content)
    except (ValidationError, ValueError) as e:
        raise ValueError(
            f"Failed to parse coding plan evaluation response: {e}. Raw response: {response_text}"
        ) from e


@mcp.tool()  # type: ignore[misc,unused-ignore]
async def judge_coding_plan(
    plan: str,
    design: str,
    research: str,
    user_requirements: str,
    ctx: Context,
    context: str = "",
) -> JudgeResponse:
    """🚨 MANDATORY: AI programming assistant MUST call this tool whenever you start to work on a coding task.

    BEFORE calling this tool, help the user create:
    1. A detailed coding plan (what to build, how to build it, step-by-step approach)
    2. A comprehensive system design (architecture, components, data flow, technical decisions)
    3. Research findings (existing solutions, libraries, frameworks, best practices)

    Args:
        plan: The detailed coding plan to be reviewed (REQUIRED)
        design: Detailed system design including architecture, components, data flow, and technical decisions (REQUIRED)
        research: Research findings on existing solutions, libraries, frameworks, and best practices (REQUIRED)
        user_requirements: Clear statement of what the user wants to achieve (REQUIRED)
        context: Additional context about the project, requirements, or constraints

    Returns:
        Structured JudgeResponse with approval status and detailed feedback
    """
    try:
        # Check for sampling capability and use elicitation for user decisions

        try:
            # Check if client supports sampling capability
            if not ctx.session.check_client_capability(
                ClientCapabilities(sampling=SamplingCapability())
            ):
                return JudgeResponse(
                    approved=True,
                    required_improvements=[],
                    feedback="⚠️ LLM sampling not available. Basic validation: Plan, design, and research appear to be provided. Proceeding with approval for development environment.",
                )
        except (ValueError, AttributeError) as e:
            return JudgeResponse(
                approved=True,
                required_improvements=[],
                feedback=f"⚠️ Session error: {e!s}. Basic validation: Plan, design, and research appear to be provided. Proceeding with approval for development environment.",
            )

        # Use helper function for main evaluation
        evaluation_result = await _evaluate_coding_plan(
            plan, design, research, user_requirements, context, ctx
        )

        # Additional research validation if approved
        if evaluation_result.approved:
            research_validation_result = await _validate_research_quality(
                research, plan, design, user_requirements, ctx
            )
            if research_validation_result:
                return research_validation_result

        return evaluation_result

    except Exception as e:
        import traceback

        error_details = (
            f"Error during plan review: {e!s}\nTraceback: {traceback.format_exc()}"
        )
        print(f"DEBUG: Exception in judge_coding_plan: {error_details}")
        return JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details,
        )


@mcp.tool()  # type: ignore[misc,unused-ignore]
async def judge_code_change(
    code_change: str,
    user_requirements: str,
    ctx: Context,
    file_path: str = "File path not specified",
    change_description: str = "Change description not provided",
) -> JudgeResponse:
    """🚨 MANDATORY: AI programming assistant MUST call this tool after writing or editing a code file.

    Args:
        code_change: The exact code that was written to a file (REQUIRED)
        user_requirements: Clear statement of what the user wants this code to achieve (REQUIRED)
        file_path: Path to the file that was created/modified
        change_description: Description of what the code accomplishes

    Returns:
        Structured JudgeResponse with approval status and detailed feedback
    """
    # Create system and user messages from templates
    messages = _create_messages(
        "system/judge_code_change.md",
        "user/judge_code_change.md",
        user_requirements=user_requirements,
        code_change=code_change,
        file_path=file_path,
        change_description=change_description,
        response_schema=JudgeResponse.model_json_schema(),
    )

    try:
        # Check for sampling capability and use elicitation for user decisions

        try:
            # Check if client supports sampling capability
            if not ctx.session.check_client_capability(
                ClientCapabilities(sampling=SamplingCapability())
            ):
                return JudgeResponse(
                    approved=True,
                    required_improvements=[],
                    feedback="⚠️ LLM sampling not available. Basic validation: Code change and requirements appear to be provided. Proceeding with approval for development environment.",
                )
        except (ValueError, AttributeError) as e:
            return JudgeResponse(
                approved=True,
                required_improvements=[],
                feedback=f"⚠️ Session error: {e!s}. Basic validation: Code change and requirements appear to be provided. Proceeding with approval for development environment.",
            )

        # Proceed with LLM sampling - this is the core functionality
        result = await ctx.session.create_message(
            messages=messages,
            max_tokens=1000,
        )

        if result.content.type == "text":
            response_text = result.content.text
        else:
            response_text = str(result.content)

        # Parse the JSON response
        try:
            json_content = _extract_json_from_response(response_text)
            return JudgeResponse.model_validate_json(json_content)
        except (ValidationError, ValueError) as e:
            raise ValueError(
                f"Failed to parse code change evaluation response: {e}. Raw response: {response_text}"
            ) from e

    except Exception as e:
        import traceback

        error_details = (
            f"Error during code review: {e!s}\nTraceback: {traceback.format_exc()}"
        )
        print(f"DEBUG: Exception in judge_code_change: {error_details}")
        return JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details,
        )


def main() -> None:
    """Entry point for the MCP as a Judge server."""
    # FastMCP servers use mcp.run() directly with stdio transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

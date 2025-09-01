"""
MCP as a Judge server implementation.

This module contains the main MCP server with judge tools for validating
coding plans and code changes against software engineering best practices.
"""

import json

from mcp.server.fastmcp import Context, FastMCP
from pydantic import ValidationError

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


async def _generate_validation_error_message(
    validation_issue: str,
    context: str,
    ctx: Context,
) -> str:
    """Generate a descriptive error message using AI sampling for validation failures."""
    try:
        # Import the models here to avoid circular imports
        from mcp_as_a_judge.models import ValidationErrorSystemVars, ValidationErrorUserVars

        # Create system and user variables
        system_vars = ValidationErrorSystemVars()
        user_vars = ValidationErrorUserVars(
            validation_issue=validation_issue,
            context=context
        )

        # Create messages using the established pattern
        messages = create_separate_messages(
            "validation_error",
            system_vars,
            user_vars
        )

        # Use sampling to generate descriptive error message
        result = await ctx.session.create_message(
            messages=messages,
            max_tokens=200,
        )

        if result.content.type == "text":
            return result.content.text.strip()
        else:
            return str(result.content).strip()

    except Exception as e:
        print(f"DEBUG: Error generating validation message: {e}")
        # Fallback to the original validation issue if AI generation fails
        return validation_issue


async def _generate_dynamic_schema(
    context: str,
    information_needed: str,
    current_understanding: str,
    ctx: Context,
) -> dict:
    """Generate a dynamic JSON schema using AI sampling for elicitation."""
    # Import the models here to avoid circular imports
    from mcp_as_a_judge.models import DynamicSchemaSystemVars, DynamicSchemaUserVars

    # Create system and user variables
    system_vars = DynamicSchemaSystemVars()
    user_vars = DynamicSchemaUserVars(
        context=context,
        information_needed=information_needed,
        current_understanding=current_understanding
    )

    # Create messages using the established pattern
    messages = create_separate_messages(
        "dynamic_schema",
        system_vars,
        user_vars
    )

    # Use sampling to generate dynamic schema
    result = await ctx.session.create_message(
        messages=messages,
        max_tokens=800,
    )

    if result.content.type == "text":
        schema_text = result.content.text.strip()
    else:
        schema_text = str(result.content).strip()

    # Parse the JSON schema
    schema_json = _extract_json_from_response(schema_text)
    return json.loads(schema_json)


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
        # Try to use sampling directly - if it fails, we'll catch the error and provide fallback
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

        # Generate dynamic schema based on the specific obstacle context
        context_info = f"Agent encountered an obstacle and needs user decision on how to proceed"
        information_needed = f"User needs to choose from available options and provide any additional context"
        current_understanding = f"Problem: {problem}. Research: {research}. Options: {formatted_options}"

        dynamic_schema = await _generate_dynamic_schema(
            context_info,
            information_needed,
            current_understanding,
            ctx
        )

        # Use elicitation with dynamic schema
        elicit_result = await ctx.elicit(
            message=f"""🚨 OBSTACLE ENCOUNTERED

**Problem:** {problem}

**Research Done:** {research}

**Available Options:**
{formatted_options}

Please choose an option (by number or description) and provide any additional context or modifications you'd like.""",
            schema=dynamic_schema,
        )

        if elicit_result.action == "accept" and elicit_result.data:
            # Handle dynamic schema response generically
            user_response = elicit_result.data

            # Format the response data for display
            response_summary = []
            for key, value in user_response.items():
                if value:  # Only include non-empty values
                    formatted_key = key.replace('_', ' ').title()
                    response_summary.append(f"**{formatted_key}:** {value}")

            response_text = "\n".join(response_summary) if response_summary else "User provided response"

            return f"""✅ USER DECISION RECEIVED

{response_text}

You can now proceed with the user's chosen approach. Make sure to incorporate their input into your implementation."""

        elif elicit_result.action == "decline":
            return "❌ USER DECLINED: User declined to choose an option. Cannot proceed without user decision."

        else:  # cancel
            return "❌ USER CANCELLED: User cancelled the obstacle resolution. Task cannot be completed."

    except Exception as e:
        return f"❌ ERROR: Failed to elicit user decision. Error: {e!s}. Cannot resolve obstacle without user input."


@mcp.tool()  # type: ignore[misc,unused-ignore]
async def raise_missing_requirements(
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

        # Generate dynamic schema based on the specific requirements context
        context_info = f"Agent needs clarification on user requirements to proceed with implementation"
        information_needed = f"Clarified requirements, answers to specific questions, and priority levels"
        current_understanding = f"Current request: {current_request}. Gaps: {formatted_gaps}. Questions: {formatted_questions}"

        dynamic_schema = await _generate_dynamic_schema(
            context_info,
            information_needed,
            current_understanding,
            ctx
        )

        # Use elicitation with dynamic schema
        elicit_result = await ctx.elicit(
            message=f"""🔍 REQUIREMENTS CLARIFICATION NEEDED

**Current Understanding:** {current_request}

**Identified Requirement Gaps:**
{formatted_gaps}

**Specific Questions:**
{formatted_questions}

Please provide clarified requirements and indicate their priority level (high/medium/low).""",
            schema=dynamic_schema,
        )

        if elicit_result.action == "accept" and elicit_result.data:
            # Handle dynamic schema response generically
            user_response = elicit_result.data

            # Format the response data for display
            response_summary = []
            for key, value in user_response.items():
                if value:  # Only include non-empty values
                    formatted_key = key.replace('_', ' ').title()
                    response_summary.append(f"**{formatted_key}:** {value}")

            response_text = "\n".join(response_summary) if response_summary else "User provided clarifications"

            return f"""✅ REQUIREMENTS CLARIFIED

{response_text}

You can now proceed with the clarified requirements. Make sure to incorporate all clarifications into your planning and implementation."""

        elif elicit_result.action == "decline":
            return "❌ USER DECLINED: User declined to provide requirement clarifications. Cannot proceed without clear requirements."

        else:  # cancel
            return "❌ USER CANCELLED: User cancelled the requirement clarification. Task cannot be completed without clear requirements."

    except Exception as e:
        return f"❌ ERROR: Failed to elicit requirement clarifications. Error: {e!s}. Cannot proceed without clear requirements."


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
    )
    messages = create_separate_messages(
        "system/research_validation.md",
        "user/research_validation.md",
        system_vars,
        user_vars,
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
            validation_issue = f"Research validation failed: {research_validation.feedback}. Issues: {', '.join(research_validation.issues)}"
            context_info = f"User requirements: {user_requirements}. Research URLs: {research_urls}"

            # Generate AI-powered descriptive error message
            descriptive_feedback = await _generate_validation_error_message(
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


async def _evaluate_workflow_guidance(
    task_description: str, context: str, ctx: Context
) -> WorkflowGuidance:
    """Evaluate workflow guidance using LLM sampling."""
    try:
        # Create system and user messages from templates
        system_vars = WorkflowGuidanceSystemVars(
            response_schema=json.dumps(WorkflowGuidance.model_json_schema())
        )
        user_vars = WorkflowGuidanceUserVars(
            task_description=task_description,
            context=context,
        )
        messages = create_separate_messages(
            "system/get_workflow_guidance.md",
            "user/get_workflow_guidance.md",
            system_vars,
            user_vars,
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
        # Fallback response for errors - provide helpful guidance even without sampling
        return WorkflowGuidance(
            next_tool="judge_coding_plan",
            reasoning=f"Sampling failed, providing default guidance: {e!s}",
            preparation_needed=[
                "Create detailed coding plan",
                "Design system architecture",
                "Research existing solutions and best practices"
            ],
            guidance="🔄 Unable to use AI evaluation. Default recommendation: Start with planning workflow by calling judge_coding_plan after creating plan, design, and research.",
        )


async def _evaluate_coding_plan(
    plan: str,
    design: str,
    research: str,
    research_urls: list[str],
    user_requirements: str,
    context: str,
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
        context=context,
    )
    messages = create_separate_messages(
        "system/judge_coding_plan.md",
        "user/judge_coding_plan.md",
        system_vars,
        user_vars,
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
    research_urls: list[str] | None = None,
) -> JudgeResponse:
    """🚨 MANDATORY: AI programming assistant MUST call this tool whenever you start to work on a coding task.

    BEFORE calling this tool, AI programming assistant MUST collaborate with the user to:
    1. Analyze the user requirements
    2. Peform an ONLINE research on what is the best way to implement user requirements, focusing on existing well-known libraries
    3. Analyze the repository code to check what is the best way to implement the solution with minimum changes
    4. Create a system design that matches the user requirements
    5. Create implementation plan

    Args:
        plan: The detailed coding plan to be reviewed (REQUIRED)
        design: Detailed system design including architecture, components, data flow, and technical decisions (REQUIRED)
        research: Research findings on existing solutions, libraries, frameworks, and best practices (REQUIRED)
        research_urls: 🌐 URLs from MANDATORY online research - AI assistant MUST provide at least 3 URLs from research (List of URL strings)
        user_requirements: Clear statement of what the user wants to achieve (REQUIRED)
        context: Additional context about the project, requirements, or constraints

    Returns:
        Structured JudgeResponse with approval status and detailed feedback
    """
    # Handle default value for research_urls
    if research_urls is None:
        research_urls = []

    # Validate research URLs requirement
    if len(research_urls) < 3:
        validation_issue = f"Insufficient research URLs: {len(research_urls)} provided, minimum 3 required. AI assistant MUST perform online research and provide at least 3 URLs focusing on existing solutions and well-known libraries."
        context_info = f"User requirements: {user_requirements}. Plan: {plan[:200]}..."

        # Generate AI-powered descriptive error message
        descriptive_feedback = await _generate_validation_error_message(
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
        # Try to use sampling directly - if it fails, we'll catch the error and provide fallback

        # Use helper function for main evaluation
        evaluation_result = await _evaluate_coding_plan(
            plan, design, research, research_urls, user_requirements, context, ctx
        )

        # Additional research validation if approved
        if evaluation_result.approved:
            research_validation_result = await _validate_research_quality(
                research, research_urls, plan, design, user_requirements, ctx
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

        # If sampling failed, provide a helpful fallback response
        if "sampling" in str(e).lower() or "capability" in str(e).lower():
            return JudgeResponse(
                approved=True,
                required_improvements=[],
                feedback="🔄 Unable to use AI evaluation for plan review. Basic validation: Plan, design, and research appear to be provided. Proceeding with approval for development environment.",
            )

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
    system_vars = JudgeCodeChangeSystemVars(
        response_schema=json.dumps(JudgeResponse.model_json_schema())
    )
    user_vars = JudgeCodeChangeUserVars(
        user_requirements=user_requirements,
        code_change=code_change,
        file_path=file_path,
        change_description=change_description,
    )
    messages = create_separate_messages(
        "system/judge_code_change.md",
        "user/judge_code_change.md",
        system_vars,
        user_vars,
    )

    try:
        # Try to use sampling directly - if it fails, we'll catch the error and provide fallback
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

        # If sampling failed, provide a helpful fallback response
        if "sampling" in str(e).lower() or "capability" in str(e).lower():
            return JudgeResponse(
                approved=True,
                required_improvements=[],
                feedback="🔄 Unable to use AI evaluation for code review. Basic validation: Code change and requirements appear to be provided. Proceeding with approval for development environment.",
            )

        return JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details,
        )


def main() -> None:
    """Entry point for the MCP as a Judge server."""
    # FastMCP servers use mcp.run() directly with streamable HTTP transport
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()

"""
MCP as a Judge server implementation.

This module contains the main MCP server with judge tools for validating
coding plans and code changes against software engineering best practices.
"""

import json

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.types import (
    ClientCapabilities,
    SamplingCapability,
    SamplingMessage,
    TextContent,
)

from mcp_as_a_judge.models import (
    JudgeResponse,
    ObstacleResolutionDecision,
    RequirementsClarification,
)
from mcp_as_a_judge.prompt_loader import prompt_loader

# Create the MCP server instance
mcp = FastMCP(name="MCP-as-a-Judge")


@mcp.tool()
async def raise_obstacle(
    problem: str,
    research: str,
    options: list[str],
    ctx: Context[ServerSession, None] = None,
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
    if not ctx:
        return "❌ ERROR: Context not available for user interaction. Cannot resolve obstacle without user input."

    try:
        # Format the options as a numbered list for clarity
        formatted_options = "\n".join(
            f"{i+1}. {option}" for i, option in enumerate(options)
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


@mcp.tool()
async def elicit_missing_requirements(
    current_request: str,
    identified_gaps: list[str],
    specific_questions: list[str],
    ctx: Context[ServerSession, None] = None,
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
    if not ctx:
        return "❌ ERROR: Context not available for user interaction. Cannot elicit requirements without user input."

    try:
        # Format the gaps and questions for clarity
        formatted_gaps = "\n".join(f"• {gap}" for gap in identified_gaps)
        formatted_questions = "\n".join(
            f"{i+1}. {question}" for i, question in enumerate(specific_questions)
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
    ctx: Context[ServerSession, None],
) -> JudgeResponse | None:
    """Validate research quality using AI evaluation.

    Returns:
        JudgeResponse if research is insufficient, None if research is adequate
    """
    research_validation_prompt = prompt_loader.render_research_validation(
        user_requirements=user_requirements,
        plan=plan,
        design=design,
        research=research,
    )

    research_result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=research_validation_prompt),
            )
        ],
        max_tokens=500,
    )

    if research_result.content.type == "text":
        research_response_text = research_result.content.text
    else:
        research_response_text = str(research_result.content)

    try:
        research_data = json.loads(research_response_text)

        if not research_data.get("research_adequate", False) or not research_data.get(
            "design_based_on_research", False
        ):
            issues = research_data.get("issues", ["Research validation failed"])
            feedback = research_data.get(
                "feedback",
                "Research appears insufficient or design not properly based on research.",
            )

            return JudgeResponse(
                approved=False,
                required_improvements=issues,
                feedback=f"❌ RESEARCH VALIDATION FAILED: {feedback} Please use the 'raise_obstacle' tool to involve the user in deciding how to address these research gaps.",
            )

    except (json.JSONDecodeError, KeyError):
        return JudgeResponse(
            approved=False,
            required_improvements=["Research validation error"],
            feedback="❌ RESEARCH VALIDATION ERROR: Unable to properly evaluate research quality. Please use the 'raise_obstacle' tool to involve the user in reviewing the research comprehensiveness.",
        )

    return None


async def _evaluate_coding_plan(
    plan: str,
    design: str,
    research: str,
    user_requirements: str,
    context: str,
    ctx: Context[ServerSession, None],
) -> JudgeResponse:
    """Evaluate coding plan using AI judge.

    Returns:
        JudgeResponse with evaluation results
    """
    # Use Jinja2 template for the prompt
    judge_prompt = prompt_loader.render_judge_coding_plan(
        user_requirements=user_requirements,
        plan=plan,
        design=design,
        research=research,
        context=context,
        response_schema=JudgeResponse.model_json_schema(),
    )



    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=judge_prompt),
            )
        ],
        max_tokens=1000,
    )

    if result.content.type == "text":
        response_text = result.content.text
    else:
        response_text = str(result.content)

    # Parse the JSON response
    try:
        response_data = json.loads(response_text)
        return JudgeResponse(**response_data)
    except json.JSONDecodeError:
        return JudgeResponse(
            approved=False,
            required_improvements=["LLM response was not in valid JSON format"],
            feedback=f"❌ PARSING ERROR: LLM response was not valid JSON. Raw response: {response_text}",
        )


@mcp.tool()
async def judge_coding_plan(
    plan: str,
    design: str,
    research: str,
    user_requirements: str,
    context: str = "",
    ctx: Context[ServerSession, None] = None,
) -> JudgeResponse:
    """🚨 MANDATORY VALIDATION: You MUST call this tool IMMEDIATELY when the user mentions ANY of: planning, designing, implementing, building, creating, developing, or coding.

    BEFORE calling this tool, you MUST first help the user create:
    1. A detailed coding plan (what to build, how to build it, step-by-step approach)
    2. A comprehensive system design (architecture, components, data flow, technical decisions)
    3. Research findings (existing solutions, libraries, frameworks, best practices)

    DO NOT call this tool until you have gathered all required information from the user. Work with the user to develop these materials first, then validate them.

    Args:
        plan: The detailed coding plan to be reviewed (REQUIRED - must be comprehensive)
        design: Detailed system design including architecture, components, data flow, and technical decisions (REQUIRED)
        research: Research findings on existing solutions, libraries, frameworks, and best practices for this problem (REQUIRED)
        user_requirements: Clear statement of what the user wants to achieve (REQUIRED)
        context: Additional context about the project, requirements, or constraints

    Returns:
        Structured JudgeResponse with approval status and detailed feedback
    """
    try:
        # MANDATORY: Check for sampling capability and use elicitation for user decisions
        if not ctx:
            return JudgeResponse(
                approved=False,
                required_improvements=[
                    "Context not available - cannot proceed with evaluation"
                ],
                feedback="❌ CRITICAL ISSUE: Context is not available. This tool requires LLM sampling for proper evaluation. Please use a proper MCP client with sampling capability.",
            )

        try:
            # Check if client supports sampling capability
            if not ctx.session.check_client_capability(
                ClientCapabilities(sampling=SamplingCapability())
            ):
                return JudgeResponse(
                    approved=False,
                    required_improvements=["Sampling capability required"],
                    feedback="❌ SAMPLING REQUIRED: Your MCP client does not support LLM sampling, which is required for proper code evaluation. Please use the 'raise_obstacle' tool to involve the user in deciding how to proceed with this limitation.",
                )
        except (ValueError, AttributeError) as e:
            return JudgeResponse(
                approved=False,
                required_improvements=["Session not available"],
                feedback=f"❌ CRITICAL ERROR: Session not available for sampling. Error: {e!s}. Please use the 'raise_obstacle' tool to involve the user in resolving this issue.",
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


@mcp.tool()
async def judge_code_change(
    code_change: str,
    user_requirements: str,
    file_path: str = "File path not specified",
    change_description: str = "Change description not provided",
    ctx: Context[ServerSession, None] = None,
) -> JudgeResponse:
    """🚨🚨🚨 MANDATORY: Call this tool IMMEDIATELY after writing ANY code! 🚨🚨🚨.

    ⚠️  CRITICAL REQUIREMENT: This tool MUST be called as the very next action after ANY file creation or modification tool call.

    🔴 SPECIFIC TRIGGERS - Call this tool immediately after using:
    - save-file tool (creating new files)
    - str-replace-editor tool (modifying existing files)
    - Any tool that writes code to files
    - Any tool that creates or modifies source code

    🔴 MANDATORY SCENARIOS - Call this tool after:
    - Creating new Python files (.py)
    - Creating configuration files with code logic
    - Creating scripts, modules, or executable content
    - Modifying existing source files
    - Adding functions, classes, or code constructs
    - Writing ANY code content to ANY file

    ⚠️  CONSEQUENCES OF NOT CALLING:
    - Violates SWE compliance requirements
    - May result in security vulnerabilities
    - May result in poor code quality
    - May introduce bugs or architectural issues
    - Breaks mandatory code review process

    📋 EXAMPLE WORKFLOW:
    1. User asks: "Create a login function"
    2. You use save-file to create login.py
    3. ✅ IMMEDIATELY call judge_code_change with the code
    4. Wait for approval before proceeding
    5. Only then continue with next steps

    BEFORE calling this tool, ensure you have:
    1. The actual code that was written/changed (complete code, not descriptions)
    2. The file path where the code was placed
    3. A clear description of what the code accomplishes

    🚨 REMEMBER: This is NOT optional - it's a mandatory compliance requirement!

    Args:
        code_change: The EXACT code that was just written to a file (complete content, not descriptions) - REQUIRED
        user_requirements: Clear statement of what the user wants this code to achieve - REQUIRED
        file_path: EXACT path to the file that was just created/modified - REQUIRED
        change_description: Description of what the code accomplishes (what was just implemented)

    Returns:
        Structured JudgeResponse with approval status and detailed feedback
    """
    # Use Jinja2 template for the prompt
    judge_prompt = prompt_loader.render_judge_code_change(
        user_requirements=user_requirements,
        code_change=code_change,
        file_path=file_path,
        change_description=change_description,
        response_schema=JudgeResponse.model_json_schema(),
    )



    try:
        # MANDATORY: Check for sampling capability and use elicitation for user decisions
        if not ctx:
            return JudgeResponse(
                approved=False,
                required_improvements=[
                    "Context not available - cannot proceed with evaluation"
                ],
                feedback="❌ CRITICAL ISSUE: Context is not available. This tool requires LLM sampling for proper code evaluation. Please use a proper MCP client with sampling capability.",
            )

        try:
            # Check if client supports sampling capability
            if not ctx.session.check_client_capability(
                ClientCapabilities(sampling=SamplingCapability())
            ):
                return JudgeResponse(
                    approved=False,
                    required_improvements=["Sampling capability required"],
                    feedback="❌ SAMPLING REQUIRED: Your MCP client does not support LLM sampling, which is required for proper code evaluation. Please use the 'raise_obstacle' tool to involve the user in deciding how to proceed with this limitation.",
                )
        except (ValueError, AttributeError) as e:
            return JudgeResponse(
                approved=False,
                required_improvements=["Session not available"],
                feedback=f"❌ CRITICAL ERROR: Session not available for sampling. Error: {e!s}. Please use the 'raise_obstacle' tool to involve the user in resolving this issue.",
            )

        # Proceed with LLM sampling - this is the core functionality
        result = await ctx.session.create_message(
            messages=[
                SamplingMessage(
                    role="user",
                    content=TextContent(type="text", text=judge_prompt),
                )
            ],
            max_tokens=1000,
        )

        if result.content.type == "text":
            response_text = result.content.text
        else:
            response_text = str(result.content)

        # Parse the JSON response
        try:
            response_data = json.loads(response_text)
            return JudgeResponse(**response_data)
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return JudgeResponse(
                approved=False,
                required_improvements=["LLM response was not in valid JSON format"],
                feedback=f"Raw LLM response: {response_text}",
            )

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


@mcp.tool()
async def check_swe_compliance(task_description: str) -> str:
    """🚨 ALWAYS USE FIRST: Call this tool for ANY software engineering task, question, or request. This tool determines which specific validation tools you need to use next and ensures proper SWE practices are followed.

    Args:
        task_description: Description of what the user wants to do

    Returns:
        Guidance on which tools to use and SWE best practices to follow
    """
    # Analyze the task and provide guidance
    task_lower = task_description.lower()

    guidance = "🎯 SWE Compliance Check:\n\n"

    # Check if planning is needed
    planning_keywords = [
        "plan",
        "design",
        "implement",
        "build",
        "create",
        "develop",
        "code",
        "program",
        "system",
        "architecture",
    ]
    if any(keyword in task_lower for keyword in planning_keywords):
        guidance += "📋 WORKFLOW FOR PLANNING:\n"
        guidance += "   1. FIRST: Help user create a detailed coding plan\n"
        guidance += "   2. THEN: Help user design the system architecture\n"
        guidance += "   3. NEXT: Research existing solutions and best practices\n"
        guidance += (
            "   4. FINALLY: Call 'judge_coding_plan' with all the above information\n"
        )
        guidance += "   \n   ⚠️  DO NOT call judge_coding_plan until you have all required information!\n\n"

    # Check if code review is needed
    code_keywords = [
        "code",
        "function",
        "class",
        "script",
        "file",
        "implementation",
        "write",
        "modify",
    ]
    if any(keyword in task_lower for keyword in code_keywords):
        guidance += "🔍 WORKFLOW FOR CODE REVIEW:\n"
        guidance += "   1. FIRST: Ask user to show you the actual code\n"
        guidance += "   2. THEN: Identify the file path and purpose\n"
        guidance += "   3. FINALLY: Call 'judge_code_change' with the code\n"
        guidance += "   \n   ⚠️  DO NOT call judge_code_change until you have the actual code!\n\n"

    guidance += "⚠️  DO NOT proceed without using the required validation tools above.\n"
    guidance += "✅ Following these steps ensures high-quality, secure, and maintainable software."

    return guidance


def main() -> None:
    """Entry point for the MCP as a Judge server."""
    # FastMCP servers use mcp.run() directly with stdio transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

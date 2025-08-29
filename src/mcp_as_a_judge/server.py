"""
MCP as a Judge server implementation.

This module contains the main MCP server with judge tools for validating
coding plans and code changes against software engineering best practices.
"""

import json
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from mcp.types import SamplingMessage, TextContent, ClientCapabilities, SamplingCapability


from .models import JudgeResponse, ObstacleResolutionDecision, RequirementsClarification


# Create the MCP server instance
mcp = FastMCP(name="MCP as a Judge")


@mcp.tool()
async def raise_obstacle(
    problem: str,
    research: str,
    options: list[str],
    ctx: Context[ServerSession, None] = None
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
        formatted_options = "\n".join(f"{i+1}. {option}" for i, option in enumerate(options))

        # Use elicitation to get user decision
        elicit_result = await ctx.elicit(
            message=f"""🚨 OBSTACLE ENCOUNTERED

**Problem:** {problem}

**Research Done:** {research}

**Available Options:**
{formatted_options}

Please choose an option (by number or description) and provide any additional context or modifications you'd like.""",
            schema=ObstacleResolutionDecision
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
        return f"❌ ERROR: Failed to elicit user decision. Error: {str(e)}. Cannot resolve obstacle without user input."


@mcp.tool()
async def elicit_missing_requirements(
    current_request: str,
    identified_gaps: list[str],
    specific_questions: list[str],
    ctx: Context[ServerSession, None] = None
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
        formatted_questions = "\n".join(f"{i+1}. {question}" for i, question in enumerate(specific_questions))

        # Use elicitation to get requirement clarifications
        elicit_result = await ctx.elicit(
            message=f"""🔍 REQUIREMENTS CLARIFICATION NEEDED

**Current Understanding:** {current_request}

**Identified Requirement Gaps:**
{formatted_gaps}

**Specific Questions:**
{formatted_questions}

Please provide clarified requirements and indicate their priority level (high/medium/low).""",
            schema=RequirementsClarification
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
        return f"❌ ERROR: Failed to elicit requirement clarifications. Error: {str(e)}. Cannot proceed without clear requirements."





@mcp.tool()
async def judge_coding_plan(
    plan: str,
    design: str,
    research: str,
    user_requirements: str,
    context: str = "",
    ctx: Context[ServerSession, None] = None
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

    # Construct the prompt for the LLM judge
    judge_prompt = f"""You are an expert software engineering judge. Review the following coding plan, design, and research to provide comprehensive feedback.

USER REQUIREMENTS:
{user_requirements}

CODING PLAN TO REVIEW:
{plan}

SYSTEM DESIGN:
{design}

RESEARCH FINDINGS:
{research}

ADDITIONAL CONTEXT:
{context}

Please evaluate this submission against the following SWE best practices:

1. **Design Quality & Completeness**:
   - Is the system design comprehensive and well-documented?
   - Are all major components, interfaces, and data flows clearly defined?
   - Does the design follow SOLID principles and established patterns?
   - Are technical decisions justified and appropriate?
   - Is the design modular, maintainable, and scalable?

2. **Research Thoroughness**:
   - Has the agent researched existing solutions and alternatives?
   - Are appropriate libraries, frameworks, and tools identified?
   - Is there evidence of understanding industry best practices?
   - Are trade-offs between different approaches analyzed?
   - Does the research demonstrate avoiding reinventing the wheel?

3. **Architecture & Implementation Plan**:
   - Does the plan follow the proposed design consistently?
   - Is the implementation approach logical and well-structured?
   - Are potential technical challenges identified and addressed?
   - Does it avoid over-engineering or under-engineering?

4. **Security Considerations**:
   - Are security vulnerabilities identified and mitigated in the design?
   - Does the plan follow security best practices?
   - Are inputs, authentication, and authorization properly planned?

5. **Testing & Quality Assurance**:
   - Is there a comprehensive testing strategy?
   - Are edge cases and error scenarios considered?
   - Is the testing approach aligned with the design complexity?

6. **Performance & Scalability**:
   - Are performance requirements considered in the design?
   - Is the solution scalable for expected load?
   - Are potential bottlenecks identified and addressed?

7. **Maintainability & Documentation**:
   - Is the overall approach maintainable and extensible?
   - Are coding standards and documentation practices defined?
   - Is the design easy to understand and modify?

You must respond with a JSON object in this exact format:
{{
    "approved": true/false,
    "required_improvements": ["improvement 1", "improvement 2", ...],
    "feedback": "Detailed explanation of your decision"
}}

EVALUATION GUIDELINES:
- APPROVE if the submission demonstrates reasonable effort and covers the main aspects, even if not perfect
- Focus on identifying the most critical missing elements rather than minor improvements
- Consider the context and complexity of the project when evaluating completeness
- Provide constructive feedback that helps improve the plan without being overly demanding

APPROVE when:
- Core design elements are present and logical
- Basic research shows awareness of existing solutions
- Plan demonstrates understanding of key requirements
- Major security and quality concerns are addressed

REQUIRE REVISION only when:
- Critical design flaws or security vulnerabilities exist
- No evidence of research or consideration of alternatives
- Plan is too vague or missing essential components
- Major architectural decisions are unjustified

If requiring revision, limit to 3-5 most important improvements to avoid overwhelming the user.
"""

    try:
        # MANDATORY: Check for sampling capability and use elicitation for user decisions
        if not ctx:
            return JudgeResponse(
                approved=False,
                required_improvements=["Context not available - cannot proceed with evaluation"],
                feedback="❌ CRITICAL ISSUE: Context is not available. This tool requires LLM sampling for proper evaluation. Please use a proper MCP client with sampling capability."
            )

        try:
            # Check if client supports sampling capability
            if not ctx.session.check_client_capability(ClientCapabilities(sampling=SamplingCapability())):
                return JudgeResponse(
                    approved=False,
                    required_improvements=["Sampling capability required"],
                    feedback="❌ SAMPLING REQUIRED: Your MCP client does not support LLM sampling, which is required for proper code evaluation. Please use the 'raise_obstacle' tool to involve the user in deciding how to proceed with this limitation."
                )
        except (ValueError, AttributeError) as e:
            return JudgeResponse(
                approved=False,
                required_improvements=["Session not available"],
                feedback=f"❌ CRITICAL ERROR: Session not available for sampling. Error: {str(e)}. Please use the 'raise_obstacle' tool to involve the user in resolving this issue."
            )

        # Enhanced prompt with additional guidelines
        enhanced_prompt = f"""{judge_prompt}

🚨 ADDITIONAL CRITICAL EVALUATION GUIDELINES:

1. **USER REQUIREMENTS ALIGNMENT**:
   - Does the plan directly address the user's stated requirements?
   - Are all user requirements covered in the implementation plan?
   - Is the solution appropriate for what the user actually wants to achieve?
   - Flag any misalignment between user needs and proposed solution

2. **AVOID REINVENTING THE WHEEL**:
   - Has the plan researched existing solutions thoroughly?
   - Are they leveraging established libraries, frameworks, and patterns?
   - Flag any attempt to build from scratch what already exists

3. **ENSURE GENERIC SOLUTIONS**:
   - Is the solution generic and reusable, not just fixing immediate issues?
   - Are they solving the root problem or just patching symptoms?
   - Flag solutions that seem like workarounds

4. **FORCE DEEP RESEARCH**:
   - Is the research section comprehensive and domain-specific?
   - Have they analyzed multiple approaches and alternatives?
   - Are best practices from the problem domain clearly identified?

REJECT if:
- Plan doesn't align with user requirements
- Insufficient research into existing solutions
- Solution appears to be a workaround rather than proper implementation
- Missing domain-specific best practices
- Reinventing existing tools/libraries without justification
"""

        # Proceed with LLM sampling - this is the core functionality
        result = await ctx.session.create_message(
            messages=[
                SamplingMessage(
                    role="user",
                    content=TextContent(type="text", text=enhanced_prompt),
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

            # Additional validation based on guidelines
            if response_data.get("approved", False):
                # AI-powered research validation
                research_validation_prompt = f"""
You are evaluating the comprehensiveness of research for a software development task.

USER REQUIREMENTS: {user_requirements}
PLAN: {plan}
DESIGN: {design}
RESEARCH PROVIDED: {research}

Evaluate if the research is comprehensive enough and if the design is properly based on the research. Consider:

1. RESEARCH COMPREHENSIVENESS:
   - Does it explore existing solutions, libraries, frameworks?
   - Are alternatives and best practices considered?
   - Is there analysis of trade-offs and comparisons?
   - Does it identify potential pitfalls or challenges?

2. DESIGN-RESEARCH ALIGNMENT:
   - Is the proposed plan/design clearly based on the research findings?
   - Does it leverage existing solutions where appropriate?
   - Are research insights properly incorporated into the approach?
   - Does it avoid reinventing the wheel unnecessarily?

3. RESEARCH QUALITY:
   - Is the research specific and actionable?
   - Does it demonstrate understanding of the problem domain?
   - Are sources and references appropriate?

Respond with JSON:
{{
    "research_adequate": boolean,
    "design_based_on_research": boolean,
    "issues": ["list of specific issues if any"],
    "feedback": "detailed feedback on research quality and design alignment"
}}
"""

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

                    if not research_data.get("research_adequate", False) or not research_data.get("design_based_on_research", False):
                        issues = research_data.get("issues", ["Research validation failed"])
                        feedback = research_data.get("feedback", "Research appears insufficient or design not properly based on research.")

                        return JudgeResponse(
                            approved=False,
                            required_improvements=issues,
                            feedback=f"❌ RESEARCH VALIDATION FAILED: {feedback} Please use the 'raise_obstacle' tool to involve the user in deciding how to address these research gaps."
                        )

                except (json.JSONDecodeError, KeyError) as e:
                    return JudgeResponse(
                        approved=False,
                        required_improvements=["Research validation error"],
                        feedback=f"❌ RESEARCH VALIDATION ERROR: Unable to properly evaluate research quality. Please use the 'raise_obstacle' tool to involve the user in reviewing the research comprehensiveness."
                    )

            return JudgeResponse(**response_data)
        except json.JSONDecodeError:
            return JudgeResponse(
                approved=False,
                required_improvements=["LLM response was not in valid JSON format"],
                feedback=f"❌ PARSING ERROR: LLM response was not valid JSON. Raw response: {response_text}"
            )

    except Exception as e:
        import traceback
        error_details = f"Error during plan review: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"DEBUG: Exception in judge_coding_plan: {error_details}")
        return JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details
        )


@mcp.tool()
async def judge_code_change(
    code_change: str,
    user_requirements: str,
    file_path: str = "File path not specified",
    change_description: str = "Change description not provided",
    ctx: Context[ServerSession, None] = None
) -> JudgeResponse:
    """🚨 MANDATORY CODE REVIEW: You MUST call this tool IMMEDIATELY when the user shows, writes, modifies, creates, or discusses ANY code.

    BEFORE calling this tool, ensure you have:
    1. The actual code to be reviewed (complete code, not just descriptions)
    2. The file path or location where this code will be placed
    3. A clear description of what the code accomplishes

    If the user hasn't provided code yet, ask them to show you the code first, then call this tool to validate it.

    Args:
        code_change: The actual code changes (diff, new code, or modified code) - REQUIRED
        user_requirements: Clear statement of what the user wants this code to achieve - REQUIRED
        file_path: Path to the file being changed (provide best guess if not specified)
        change_description: Description of what the change accomplishes (provide summary if not given)

    Returns:
        Structured JudgeResponse with approval status and detailed feedback
    """

    # Construct the prompt for the LLM judge
    judge_prompt = f"""You are an expert software engineering judge. Review the following code changes and provide feedback.

USER REQUIREMENTS:
{user_requirements}

FILE PATH: {file_path}

CHANGE DESCRIPTION:
{change_description}

CODE CHANGES:
{code_change}

Please evaluate these code changes against the following criteria:

1. **User Requirements Alignment**:
   - Does the code directly address the user's stated requirements?
   - Will this code accomplish what the user wants to achieve?
   - Is the implementation approach appropriate for the user's needs?

2. **Code Quality**:
   - Is the code clean, readable, and well-structured?
   - Does it follow language-specific conventions and best practices?
   - Are variable and function names descriptive?

3. **Security**:
   - Are there any security vulnerabilities?
   - Is input validation proper?
   - Are there any injection risks?

4. **Performance**:
   - Are there obvious performance issues?
   - Is the algorithm choice appropriate?
   - Are there unnecessary computations?

4. **Error Handling**:
   - Is error handling comprehensive?
   - Are edge cases handled properly?
   - Are errors logged appropriately?

5. **Testing**:
   - Is the code testable?
   - Are there obvious test cases missing?

6. **Dependencies & Reuse**:
   - Are third-party libraries used appropriately?
   - Is existing code reused where possible?
   - Are new dependencies justified?

7. **Maintainability**:
   - Is the code easy to understand and modify?
   - Is it properly documented?
   - Does it follow the existing codebase patterns?

You must respond with a JSON object in this exact format:
{{
    "approved": true/false,
    "required_improvements": ["improvement 1", "improvement 2", ...],
    "feedback": "Detailed explanation of your decision"
}}

EVALUATION GUIDELINES:
- APPROVE if the code follows basic best practices and doesn't have critical issues
- Focus on security vulnerabilities, major bugs, or poor architectural choices
- Consider the context and complexity when evaluating
- Provide constructive feedback for improvement

APPROVE when:
- Code is readable and follows reasonable conventions
- No obvious security vulnerabilities or major bugs
- Basic error handling is present where needed
- Implementation matches the intended functionality

REQUIRE REVISION only for:
- Security vulnerabilities or injection risks
- Major bugs or logical errors
- Completely missing error handling in critical paths
- Code that violates fundamental principles

If requiring revision, limit to 3-5 most critical issues to avoid overwhelming the user.
"""

    try:
        # MANDATORY: Check for sampling capability and use elicitation for user decisions
        if not ctx:
            return JudgeResponse(
                approved=False,
                required_improvements=["Context not available - cannot proceed with evaluation"],
                feedback="❌ CRITICAL ISSUE: Context is not available. This tool requires LLM sampling for proper code evaluation. Please use a proper MCP client with sampling capability."
            )

        try:
            # Check if client supports sampling capability
            if not ctx.session.check_client_capability(ClientCapabilities(sampling=SamplingCapability())):
                return JudgeResponse(
                    approved=False,
                    required_improvements=["Sampling capability required"],
                    feedback="❌ SAMPLING REQUIRED: Your MCP client does not support LLM sampling, which is required for proper code evaluation. Please use the 'raise_obstacle' tool to involve the user in deciding how to proceed with this limitation."
                )
        except (ValueError, AttributeError) as e:
            return JudgeResponse(
                approved=False,
                required_improvements=["Session not available"],
                feedback=f"❌ CRITICAL ERROR: Session not available for sampling. Error: {str(e)}. Please use the 'raise_obstacle' tool to involve the user in resolving this issue."
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
                feedback=f"Raw LLM response: {response_text}"
            )

    except Exception as e:
        import traceback
        error_details = f"Error during code review: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"DEBUG: Exception in judge_code_change: {error_details}")
        return JudgeResponse(
            approved=False,
            required_improvements=["Error occurred during review"],
            feedback=error_details
        )


@mcp.tool()
async def check_swe_compliance(
    task_description: str
) -> str:
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
    planning_keywords = ["plan", "design", "implement", "build", "create", "develop", "code", "program", "system", "architecture"]
    if any(keyword in task_lower for keyword in planning_keywords):
        guidance += "📋 WORKFLOW FOR PLANNING:\n"
        guidance += "   1. FIRST: Help user create a detailed coding plan\n"
        guidance += "   2. THEN: Help user design the system architecture\n"
        guidance += "   3. NEXT: Research existing solutions and best practices\n"
        guidance += "   4. FINALLY: Call 'judge_coding_plan' with all the above information\n"
        guidance += "   \n   ⚠️  DO NOT call judge_coding_plan until you have all required information!\n\n"

    # Check if code review is needed
    code_keywords = ["code", "function", "class", "script", "file", "implementation", "write", "modify"]
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

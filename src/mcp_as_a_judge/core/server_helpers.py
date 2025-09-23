"""
Helper functions for the MCP as a Judge server.

This module contains utility functions used by the server for JSON processing,
dynamic model generation, validation, and LLM configuration.
"""

import json
import re
from typing import Any

from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field, ValidationError

from mcp_as_a_judge.core.constants import MAX_TOKENS
from mcp_as_a_judge.core.logging_config import get_logger
from mcp_as_a_judge.llm.llm_integration import load_llm_config_from_env
from mcp_as_a_judge.messaging.llm_provider import llm_provider
from mcp_as_a_judge.prompting.loader import create_separate_messages


def get_session_id(ctx: Context) -> str:
    """Extract session_id from context, with fallback to default."""
    return getattr(ctx, "session_id", "default_session")


def initialize_llm_configuration() -> None:
    """Initialize LLM configuration from environment variables.

    This function loads LLM configuration from environment variables and
    configures the LLM manager if a valid configuration is found.
    Logs status messages to inform users about the configuration state.
    """
    logger = get_logger(__name__)
    # Do not auto-configure LLM from environment during server startup to keep
    # tests deterministic and avoid unintended provider availability.
    # Callers can configure llm_manager explicitly if needed.
    llm_config = load_llm_config_from_env()
    if llm_config:
        logger.info(
            "LLM configuration detected in environment (not auto-enabled during startup)."
        )
    else:
        logger.info(
            "No LLM API key found in environment. MCP sampling will be required."
        )


def extract_json_from_response(response_text: str) -> str:
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
    first_brace = response_text.find("{")
    last_brace = response_text.rfind("}")

    if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
        response_info = {
            "length": len(response_text),
            "is_empty": len(response_text.strip()) == 0,
            "first_100_chars": response_text[:100] if response_text else "None",
            "contains_json_markers": "{" in response_text and "}" in response_text,
        }
        raise ValueError(
            f"No valid JSON object found in response. "
            f"Response info: {response_info}. "
            f"Full response: '{response_text}'"
        )

    json_content = response_text[first_brace : last_brace + 1]
    return json_content


async def generate_validation_error_message(
    validation_issue: str,
    context: str,
    ctx: Context,
) -> str:
    """Generate a descriptive error message using AI sampling for validation failures."""
    try:
        from mcp_as_a_judge.models import (
            SystemVars,
            ValidationErrorUserVars,
        )

        system_vars = SystemVars(max_tokens=MAX_TOKENS)
        user_vars = ValidationErrorUserVars(
            validation_issue=validation_issue, context=context
        )

        messages = create_separate_messages(
            "system/validation_error.md",
            "user/validation_error.md",
            system_vars,
            user_vars,
        )

        response_text = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=MAX_TOKENS,
            prefer_sampling=True,  # gitleaks:allow
        )
        return response_text.strip()

    except Exception:
        return validation_issue


async def generate_dynamic_elicitation_model(
    context: str,
    information_needed: str,
    current_understanding: str,
    ctx: Context,
) -> type[BaseModel]:
    """Generate a dynamic Pydantic model for elicitation based on context.

    This function uses LLM to generate field definitions and creates a proper
    Pydantic BaseModel class that's compatible with MCP elicitation.

    Args:
        context: Context about what information needs to be gathered
        information_needed: Specific description of what information is needed
        current_understanding: What we currently understand about the situation
        ctx: MCP context for LLM communication

    Returns:
        Dynamically created Pydantic BaseModel class
    """
    try:
        from mcp_as_a_judge.models import DynamicSchemaUserVars, SystemVars

        system_vars = SystemVars(max_tokens=MAX_TOKENS)
        user_vars = DynamicSchemaUserVars(
            context=context,
            information_needed=information_needed,
            current_understanding=current_understanding,
        )

        messages = create_separate_messages(
            "system/dynamic_schema.md", "user/dynamic_schema.md", system_vars, user_vars
        )

        # Use LLM to generate field definitions
        schema_text = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=MAX_TOKENS,
            prefer_sampling=True,  # gitleaks:allow
        )

        # Parse the field definitions JSON
        fields_json = extract_json_from_response(schema_text)
        fields_dict = json.loads(fields_json)

        # Convert field definitions to Pydantic model
        return create_pydantic_model_from_fields(fields_dict)

    except Exception:
        # If dynamic generation fails, re-raise the exception
        # All fields MUST be resolved by LLM - no static fallback
        raise


async def extract_latest_workflow_guidance(
    conversation_history: list[dict],
) -> dict | None:
    """Extract the latest workflow guidance from conversation history.

    Args:
        conversation_history: List of conversation records

    Returns:
        Latest workflow guidance object, or None if not found
    """
    # Search through conversation history for the most recent workflow guidance
    for record in conversation_history:
        try:
            output_data = json.loads(record.get("output", "{}"))
            if isinstance(output_data, dict) and "workflow_guidance" in output_data:
                guidance_data = output_data["workflow_guidance"]
                if isinstance(guidance_data, dict):
                    # Return the full guidance object for structured access
                    return guidance_data
        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    return None


async def validate_research_quality(
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
    from mcp_as_a_judge.models import (
        ResearchValidationResponse,
        ResearchValidationUserVars,
        SystemVars,
    )

    # Create system and user messages for research validation
    system_vars = SystemVars(
        response_schema=json.dumps(ResearchValidationResponse.model_json_schema()),
        max_tokens=MAX_TOKENS,
    )
    user_vars = ResearchValidationUserVars(
        user_requirements=user_requirements,
        plan=plan,
        design=design,
        research=research,
        research_urls=research_urls,
        context="",
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

    # LLM-driven aspects extraction and coverage validation (no hardcoded topics)
    try:
        from mcp_as_a_judge.tasks.research import (
            analyze_research_aspects,
            validate_aspect_coverage,
        )

        aspects = await analyze_research_aspects(
            task_title="",
            task_description="",
            user_requirements=user_requirements,
            plan=plan,
            design=design,
            ctx=ctx,
        )
        covered, missing = validate_aspect_coverage(research, research_urls, aspects)
        if not covered and missing:
            issue = "Insufficient research coverage for required aspects"
            descriptive_feedback = await generate_validation_error_message(
                issue,
                f"Missing aspects: {', '.join(missing)}. URLs provided: {research_urls}",
                ctx,
            )
            return {
                "approved": False,
                "required_improvements": [
                    f"Add authoritative research covering: {name}" for name in missing
                ],
                "feedback": descriptive_feedback,
            }
    except Exception:  # nosec B110
        # Be resilient; failing aspects extraction should not crash validation
        pass

    return None


async def evaluate_coding_plan(
    plan: str,
    design: str,
    research: str,
    research_urls: list[str],
    user_requirements: str,
    context: str,
    conversation_history: list[dict],
    task_metadata: Any,  # TaskMetadata type - avoiding import to prevent circular dependency
    ctx: Context,
    problem_domain: str = "",
    problem_non_goals: list[str] = [],  # noqa: B006
    library_plan: list[dict] = [],  # noqa: B006
    internal_reuse_components: list[dict] = [],  # noqa: B006
    design_patterns: list[dict] = [],  # noqa: B006
    identified_risks_override: list[str] = [],  # noqa: B006
    risk_mitigation_override: list[str] = [],  # noqa: B006
) -> Any:
    """Evaluate coding plan using AI judge.

    Returns:
        JudgeResponse with evaluation results
    """
    from mcp_as_a_judge.models import (
        DesignPattern,
        JudgeCodingPlanUserVars,
        SystemVars,
    )
    from mcp_as_a_judge.models.enhanced_responses import JudgeResponse

    # Extract the latest workflow guidance from conversation history
    workflow_guidance_obj = await extract_latest_workflow_guidance(conversation_history)

    # Format workflow guidance for the system prompt
    workflow_guidance_text = ""
    if workflow_guidance_obj:
        # Create a comprehensive guidance text that includes all structured information
        guidance_parts = []

        if workflow_guidance_obj.get("next_tool"):
            guidance_parts.append(
                f"**Next Tool:** {workflow_guidance_obj['next_tool']}"
            )

        if workflow_guidance_obj.get("reasoning"):
            guidance_parts.append(
                f"**Reasoning:** {workflow_guidance_obj['reasoning']}"
            )

        if workflow_guidance_obj.get("preparation_needed"):
            prep_items = workflow_guidance_obj["preparation_needed"]
            if isinstance(prep_items, list) and prep_items:
                guidance_parts.append("**Preparation Required:**")
                for item in prep_items:
                    guidance_parts.append(f"- {item}")

        if workflow_guidance_obj.get("plan_required_fields"):
            fields = workflow_guidance_obj["plan_required_fields"]
            if isinstance(fields, list) and fields:
                guidance_parts.append("**Required Plan Fields:**")
                for field in fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "unknown")
                        field_type = field.get("type", "unknown")
                        field_desc = field.get("description", "")
                        required = field.get("required", False)
                        conditional = field.get("conditional_on", "")

                        field_info = f"- **{field_name}** ({field_type})"
                        if required:
                            field_info += " [REQUIRED]"
                        if conditional:
                            field_info += f" [Conditional on: {conditional}]"
                        if field_desc:
                            field_info += f": {field_desc}"
                        guidance_parts.append(field_info)

        if workflow_guidance_obj.get("guidance"):
            guidance_parts.append(
                f"**Detailed Guidance:** {workflow_guidance_obj['guidance']}"
            )

        workflow_guidance_text = "\n".join(guidance_parts)

    # Generate plan required fields for dynamic validation
    from mcp_as_a_judge.workflow.workflow_guidance import _generate_plan_required_fields

    plan_required_fields = _generate_plan_required_fields(task_metadata)
    plan_required_fields_json = json.dumps(
        [field.model_dump() for field in plan_required_fields], indent=2
    )

    # Create system and user messages from templates
    system_vars = SystemVars(
        response_schema=json.dumps(JudgeResponse.model_json_schema()),
        max_tokens=MAX_TOKENS,
        workflow_guidance=workflow_guidance_text,
        plan_required_fields_json=plan_required_fields_json,
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
        research_required=task_metadata.research_required
        if task_metadata.research_required is not None
        else False,
        research_scope=task_metadata.research_scope.value
        if task_metadata.research_scope
        else "none",
        research_rationale=task_metadata.research_rationale or "",
        # Conditional internal research fields - LLM will determine these during evaluation
        internal_research_required=task_metadata.internal_research_required
        if task_metadata.internal_research_required is not None
        else False,
        related_code_snippets=task_metadata.related_code_snippets or [],
        # Conditional risk assessment fields - LLM will determine these during evaluation
        risk_assessment_required=task_metadata.risk_assessment_required
        if task_metadata.risk_assessment_required is not None
        else False,
        identified_risks=(
            identified_risks_override
            if identified_risks_override is not None
            else task_metadata.identified_risks or []
        ),
        risk_mitigation_strategies=(
            risk_mitigation_override
            if risk_mitigation_override is not None
            else task_metadata.risk_mitigation_strategies or []
        ),
        # Domain focus and reuse maps (optional explicit inputs)
        problem_domain=problem_domain,
        problem_non_goals=problem_non_goals,
        library_plan=library_plan,
        internal_reuse_components=internal_reuse_components,
        # Design patterns enforcement (conditional based on task metadata)
        design_patterns=[
            DesignPattern(name=dp["name"], area=dp["area"]) for dp in design_patterns
        ],
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


def create_pydantic_model_from_fields(fields_dict: dict) -> type[BaseModel]:
    """Convert field definitions to a Pydantic BaseModel class.

    Args:
        fields_dict: Dictionary where keys are field names and values are objects
                    with "required" (bool) and "description" (str) properties

    Returns:
        Dynamically created Pydantic BaseModel class
    """
    # Build field definitions for the Pydantic model
    field_definitions = {}

    for field_name, field_config in fields_dict.items():
        # Extract configuration from LLM-generated field definition
        # Handle cases where LLM returns boolean instead of dict
        if isinstance(field_config, dict):
            is_required = field_config.get("required", False)
            description = field_config.get(
                "description", field_name.replace("_", " ").title()
            )
        elif isinstance(field_config, bool):
            # LLM returned boolean - treat as required flag
            is_required = field_config
            description = field_name.replace("_", " ").title()
        else:
            # LLM returned something else (string, etc.) - treat as description
            is_required = False
            description = (
                str(field_config)
                if field_config
                else field_name.replace("_", " ").title()
            )

        # All fields are strings (text input) as per MCP elicitation constraints
        # MCP elicitation only supports primitive types, no unions like str | None
        if is_required:
            field_definitions[field_name] = (str, Field(description=description))
        else:
            # Use empty string as default for optional fields (primitive type only)
            field_definitions[field_name] = (
                str,
                Field(default="", description=description),
            )

    # Create the dynamic model class
    dynamic_elicitation_model = type(
        "DynamicElicitationModel",
        (BaseModel,),
        {
            "__annotations__": {
                name: field_def[0] for name, field_def in field_definitions.items()
            },
            **{name: field_def[1] for name, field_def in field_definitions.items()},
        },
    )

    return dynamic_elicitation_model


def looks_like_unified_diff(text: str) -> bool:
    """Check if text looks like a unified Git diff.

    Args:
        text: Text to check

    Returns:
        True if text appears to be a unified diff, False otherwise
    """
    # Accept standard unified git diffs and our patch wrapper for flexibility
    if not text:
        return False
    has_git_headers = bool(
        re.search(r"^diff --git a/.+ b/.+", text, flags=re.MULTILINE)
    )
    has_unified_hunks = all(token in text for token in ("--- ", "+++ ", "@@"))
    has_apply_patch_wrapper = "*** Begin Patch" in text
    return has_git_headers or has_unified_hunks or has_apply_patch_wrapper


def extract_changed_files(diff_text: str) -> list[str]:
    """Extract changed file paths from a unified diff.

    Args:
        diff_text: Unified diff text

    Returns:
        List of changed file paths
    """
    changed: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("+++"):
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip() != "/dev/null":
                p = parts[1].strip()
                if p.startswith("b/"):
                    p = p[2:]
                changed.add(p)
        elif line.startswith("---"):
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip() != "/dev/null":
                p = parts[1].strip()
                if p.startswith("a/"):
                    p = p[2:]
                changed.add(p)
    if not changed:
        for m in re.finditer(
            r"^diff --git a/(.+?) b/(.+)$", diff_text, flags=re.MULTILINE
        ):
            changed.add(m.group(2))
    return sorted(changed)


async def validate_test_output(
    test_output: str,
    ctx: Context,
    context: str = "",
) -> bool:
    """Validate test output using LLM evaluation instead of static patterns.

    Args:
        test_output: The test execution output to validate
        ctx: MCP context for LLM communication
        context: Additional context about the validation

    Returns:
        True if the output appears to be genuine test execution output, False otherwise
    """
    if not test_output:
        return False

    try:
        from mcp_as_a_judge.models import (
            SystemVars,
            TestOutputValidationResponse,
            TestOutputValidationUserVars,
        )

        # Create system and user messages for test output validation
        system_vars = SystemVars(
            response_schema=json.dumps(
                TestOutputValidationResponse.model_json_schema()
            ),
            max_tokens=MAX_TOKENS,
        )
        user_vars = TestOutputValidationUserVars(
            test_output=test_output,
            context=context,
        )
        messages = create_separate_messages(
            "system/test_output_validation.md",
            "user/test_output_validation.md",
            system_vars,
            user_vars,
        )

        response_text = await llm_provider.send_message(
            messages=messages, ctx=ctx, max_tokens=MAX_TOKENS, prefer_sampling=True
        )

        # Parse the JSON response
        json_content = extract_json_from_response(response_text)
        validation_result = TestOutputValidationResponse.model_validate_json(
            json_content
        )

        # Return True if it looks like test output with reasonable confidence
        return (
            validation_result.looks_like_test_output
            and validation_result.confidence_score >= 0.7
        )

    except Exception:
        # Fallback to basic pattern matching if LLM validation fails
        patterns = [
            r"collected \d+ items",  # pytest
            r"=+\s*\d+ passed",  # pytest summary
            r"\d+ passed, \d+ failed",  # common summary
            r"Ran \d+ tests in",  # unittest/pytest
            r"OK\b",  # unittest
            r"FAILURES?\b",  # unittest/pytest
            r"Test Suites?:\s*\d+\s*passed",  # jest
            r"\d+ tests? passed",  # jest/mocha
            r"go test",  # go test
            r"BUILD SUCCESS",  # maven/gradle
            r"\[INFO\].*?Surefire",  # maven surefire
            r"JUnit",  # junit marker
        ]
        return any(
            re.search(p, test_output, flags=re.IGNORECASE | re.MULTILINE)
            for p in patterns
        )


# (Removed rule-based decision extraction and gating to keep HITL LLM-driven)

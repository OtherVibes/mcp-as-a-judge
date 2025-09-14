"""
Research Requirements Analysis Module

This module provides LLM-driven analysis to determine the appropriate number
of research URLs needed for a given software development task based on
complexity, domain specialization, and implementation risk.
"""

# Import directly from models.py for the missing models
import importlib.util
import json
import os
from typing import Any

# Import directly from models.py for the missing models
from pydantic import BaseModel

from mcp_as_a_judge.core.constants import MAX_TOKENS
from mcp_as_a_judge.core.logging_config import get_logger
from mcp_as_a_judge.core.server_helpers import extract_json_from_response
from mcp_as_a_judge.messaging.llm_provider import llm_provider
from mcp_as_a_judge.models import (
    ResearchComplexityFactors,
    ResearchRequirementsAnalysis,
    ResearchRequirementsAnalysisUserVars,
    SystemVars,
    URLValidationResult,
)
from mcp_as_a_judge.models.task_metadata import TaskMetadata
from mcp_as_a_judge.prompting.loader import create_separate_messages


# Create fallback classes first
class ResearchAspectsExtraction(BaseModel):
    aspects: list = []
    notes: str = ""


class ResearchAspectsUserVars(BaseModel):
    task_title: str = ""
    task_description: str = ""
    user_requirements: str = ""
    plan: str = ""
    design: str = ""


# Try to override with the real classes from models.py
try:
    _models_py_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "models.py"
    )
    _spec = importlib.util.spec_from_file_location("models_py", _models_py_path)
    if _spec and _spec.loader:
        _models_py = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_models_py)
        # Use globals() to avoid mypy type assignment errors
        globals()["ResearchAspectsExtraction"] = _models_py.ResearchAspectsExtraction
        globals()["ResearchAspectsUserVars"] = _models_py.ResearchAspectsUserVars
except Exception:  # nosec B110
    # Use the fallback classes defined above
    pass

logger = get_logger(__name__)


async def analyze_research_requirements(
    task_metadata: TaskMetadata,
    user_requirements: str,
    ctx: Any,  # MCP Context
) -> "ResearchRequirementsAnalysis":
    """
    Analyze a task to determine dynamic research URL requirements.

    Uses LLM to assess task complexity across multiple dimensions and recommend
    appropriate research URL count and quality requirements.

    Args:
        task_metadata: Current task metadata with title, description, and research info
        user_requirements: User's specific requirements for the task
        ctx: MCP Context for LLM provider

    Returns:
        ResearchRequirementsAnalysis with URL count recommendations and reasoning

    Raises:
        ValueError: If LLM analysis fails or returns invalid response
    """
    logger.info(f"Analyzing research requirements for task: {task_metadata.title}")

    try:
        # Create system and user messages from templates
        system_vars = SystemVars(
            response_schema=json.dumps(
                ResearchRequirementsAnalysis.model_json_schema()
            ),
            max_tokens=MAX_TOKENS,
        )

        user_vars = ResearchRequirementsAnalysisUserVars(
            task_title=task_metadata.title,
            task_description=task_metadata.description,
            user_requirements=user_requirements,
            research_scope=task_metadata.research_scope.value,
            research_rationale=task_metadata.research_rationale,
            context="",  # Additional context can be added if needed
        )

        messages = create_separate_messages(
            "system/research_requirements_analysis.md",
            "user/research_requirements_analysis.md",
            system_vars,
            user_vars,
        )

        # Get LLM analysis
        response_text = await llm_provider.send_message(
            messages=messages, ctx=ctx, max_tokens=MAX_TOKENS, prefer_sampling=True
        )

        # Parse and validate the response
        json_content = extract_json_from_response(response_text)
        analysis = ResearchRequirementsAnalysis.model_validate_json(json_content)

        logger.info(
            f"Research analysis complete: Expected URLs={analysis.expected_url_count}, "
            f"Minimum URLs={analysis.minimum_url_count}"
        )

        return analysis

    except Exception as e:
        logger.error(f"Failed to analyze research requirements: {e}")
        # Return conservative default analysis
        return _get_fallback_analysis(task_metadata)


def _get_fallback_analysis(
    task_metadata: TaskMetadata,
) -> "ResearchRequirementsAnalysis":
    """
    Provide fallback analysis if LLM analysis fails.

    Uses conservative defaults based on existing research scope.
    """
    scope_to_urls = {"none": (0, 0), "light": (2, 1), "deep": (4, 2)}

    expected, minimum = scope_to_urls.get(task_metadata.research_scope.value, (3, 2))

    return ResearchRequirementsAnalysis(
        expected_url_count=expected,
        minimum_url_count=minimum,
        reasoning=f"Fallback analysis based on research scope '{task_metadata.research_scope.value}'. "
        f"LLM analysis was unavailable, so using conservative defaults.",
        complexity_factors=ResearchComplexityFactors(
            domain_specialization="general",
            technology_maturity="established",
            integration_scope="moderate",
            existing_solutions="limited",
            risk_level="medium",
        ),
        quality_requirements=[
            "Official documentation or authoritative sources",
            "Current repository analysis for existing patterns",
            "Practical implementation examples",
        ],
    )


async def validate_url_adequacy(
    provided_urls: list[str],
    expected_count: int,
    minimum_count: int,
    reasoning: str,
    ctx: Any,  # MCP Context
) -> "URLValidationResult":
    """
    Validate that provided URLs meet the dynamic requirements.

    Args:
        provided_urls: List of URLs provided for research
        expected_count: Expected number of URLs from analysis
        minimum_count: Minimum acceptable number of URLs
        reasoning: Reasoning for why these counts are needed
        ctx: MCP Context

    Returns:
        URLValidationResult with validation outcome and feedback
    """
    provided_count = len(provided_urls)

    logger.info(
        f"Validating URL adequacy: Provided={provided_count}, "
        f"Expected={expected_count}, Minimum={minimum_count}"
    )

    # Generate contextual feedback
    if provided_count == 0:
        feedback = f"No research URLs provided. {reasoning} At least {minimum_count} URLs are needed for adequate research coverage."
        adequate = False
    elif provided_count < minimum_count:
        feedback = (
            f"Insufficient research URLs provided ({provided_count} provided, {minimum_count} minimum required). "
            f"{reasoning} Please provide at least {minimum_count - provided_count} additional authoritative sources."
        )
        adequate = False
    elif provided_count < expected_count:
        feedback = (
            f"Research URLs meet minimum requirements ({provided_count}/{minimum_count}) but fall short of optimal coverage "
            f"({expected_count} recommended). {reasoning} Consider adding {expected_count - provided_count} more sources for comprehensive coverage."
        )
        adequate = True  # Meets minimum, but note the recommendation
    else:
        feedback = f"Research URL count meets expectations ({provided_count} provided, {expected_count} expected). {reasoning}"
        adequate = True

    # For now, assume quality standards are met if count is adequate
    # This could be enhanced with actual URL content analysis
    meets_quality_standards = adequate and provided_count >= minimum_count

    return URLValidationResult(
        adequate=adequate,
        provided_count=provided_count,
        expected_count=expected_count,
        minimum_count=minimum_count,
        feedback=feedback,
        meets_quality_standards=meets_quality_standards,
    )


def update_task_metadata_with_analysis(
    task_metadata: TaskMetadata, analysis: "ResearchRequirementsAnalysis"
) -> None:
    """
    Update TaskMetadata with the results of research requirements analysis.

    Args:
        task_metadata: TaskMetadata instance to update
        analysis: ResearchRequirementsAnalysis results to apply
    """
    task_metadata.expected_url_count = analysis.expected_url_count
    task_metadata.minimum_url_count = analysis.minimum_url_count
    task_metadata.url_requirement_reasoning = analysis.reasoning
    task_metadata.research_complexity_analysis = {
        "domain_specialization": analysis.complexity_factors.domain_specialization,
        "technology_maturity": analysis.complexity_factors.technology_maturity,
        "integration_scope": analysis.complexity_factors.integration_scope,
        "existing_solutions": analysis.complexity_factors.existing_solutions,
        "risk_level": analysis.complexity_factors.risk_level,
        "quality_requirements": analysis.quality_requirements,
    }

    logger.info(
        f"Updated task metadata with research analysis: "
        f"Expected={analysis.expected_url_count}, Minimum={analysis.minimum_url_count}"
    )


async def analyze_research_aspects(
    *,
    task_title: str,
    task_description: str,
    user_requirements: str,
    plan: str,
    design: str,
    ctx: Any,
) -> ResearchAspectsExtraction:
    """Use LLM to extract a generic list of research aspects to cover.

    The LLM should infer systems, frameworks, protocols, integrations, and deployment concerns
    from the requirements/plan/design, and output canonical aspect names with synonyms.
    """
    system_vars = SystemVars(
        response_schema=json.dumps(ResearchAspectsExtraction.model_json_schema()),
        max_tokens=MAX_TOKENS,
    )
    user_vars = ResearchAspectsUserVars(
        task_title=task_title,
        task_description=task_description,
        user_requirements=user_requirements,
        plan=plan,
        design=design,
    )
    messages = create_separate_messages(
        "system/research_aspects.md",
        "user/research_aspects.md",
        system_vars,
        user_vars,
    )

    try:
        response_text = await llm_provider.send_message(
            messages=messages, ctx=ctx, max_tokens=MAX_TOKENS, prefer_sampling=True
        )
        json_content = extract_json_from_response(response_text)
        aspects = ResearchAspectsExtraction.model_validate_json(json_content)
        return aspects
    except Exception as e:
        logger.warning(f"Failed to extract research aspects via LLM: {e}")
        # Fallback to empty aspects (no additional gating)
        return ResearchAspectsExtraction(aspects=[], notes="fallback-empty")


def validate_aspect_coverage(
    research_text: str, research_urls: list[str], aspects: ResearchAspectsExtraction
) -> tuple[bool, list[str]]:
    """Check that each required aspect is covered by research text or URLs using LLM-provided synonyms.

    Returns:
      (covered_fully, missing_aspect_names)
    """
    rt = (research_text or "").lower()
    url_lc = [u.lower() for u in (research_urls or [])]

    missing: list[str] = []
    for aspect in aspects.aspects:
        if not aspect.required:
            continue

        # Build a set of needles: canonical name + synonyms, lowercased and space/sep-insensitive for URLs
        needles = [aspect.name.lower()] + [s.lower() for s in (aspect.synonyms or [])]
        # Check research text
        found_text = any(n in rt for n in needles)

        # Check URLs (normalize by removing spaces for match resilience)
        def in_url(n: str) -> bool:
            n2 = n.replace(" ", "").strip()
            return any(n2 in u.replace(" ", "") for u in url_lc)

        found_url = any(in_url(n) for n in needles)

        if not (found_text or found_url):
            missing.append(aspect.name)

    return (len(missing) == 0, missing)

"""
Data models and schemas for MCP as a Judge.

This module contains all Pydantic models used for data validation,
serialization, and API contracts.
"""

from typing import List
from pydantic import BaseModel, Field


class JudgeResponse(BaseModel):
    """Response model for all judge tool evaluations.

    This standardized response format ensures consistent feedback
    across all evaluation tools.
    """

    approved: bool = Field(
        description="Whether the plan/code is approved for implementation"
    )
    required_improvements: List[str] = Field(
        default_factory=list,
        description="Specific improvements needed (empty if approved)"
    )
    feedback: str = Field(
        description="Detailed explanation of the decision and recommendations"
    )


class ObstacleResolutionDecision(BaseModel):
    """Schema for eliciting user decision when agent encounters obstacles.

    Used by the raise_obstacle tool to capture user choices when
    the agent cannot proceed due to blockers or missing information.
    """

    chosen_option: str = Field(
        description="The option the user chooses from the provided list"
    )
    additional_context: str = Field(
        default="",
        description="Any additional context or modifications the user provides"
    )


class RequirementsClarification(BaseModel):
    """Schema for eliciting missing requirements from user.

    Used by the elicit_missing_requirements tool to capture
    clarified requirements when the original request is unclear.
    """

    clarified_requirements: str = Field(
        description="The clarified or additional requirements"
    )
    priority_level: str = Field(
        description="Priority level: 'high', 'medium', or 'low'"
    )
    additional_context: str = Field(
        default="",
        description="Any additional context about the requirements"
    )


class ComplianceCheckResult(BaseModel):
    """Result model for SWE compliance checks.

    Used by the check_swe_compliance tool to provide
    structured guidance on software engineering best practices.
    """

    compliance_status: str = Field(
        description="Overall compliance status: 'compliant', 'needs_improvement', 'non_compliant'"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Specific recommendations for improvement"
    )
    next_steps: List[str] = Field(
        default_factory=list,
        description="Recommended next steps in the development workflow"
    )
    guidance: str = Field(
        description="Detailed guidance on software engineering best practices"
    )


# Type aliases for better code readability
ToolResponse = JudgeResponse
ElicitationResponse = str

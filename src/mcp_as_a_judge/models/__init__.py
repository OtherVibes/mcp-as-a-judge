"""
Models package for MCP as a Judge.

This package re-exports models for convenient `from mcp_as_a_judge.models import ...`
usage. The canonical `WorkflowGuidance` lives in `workflow/workflow_guidance.py` and
is imported here for a single source of truth.
"""

import importlib.util
import os
from typing import TYPE_CHECKING
from typing import Any as _Any

from pydantic import BaseModel, Field

# Task metadata models
# Workflow guidance models
from mcp_as_a_judge.workflow import WorkflowGuidance

# Enhanced response models for workflow v3
from .enhanced_responses import (
    EnhancedResponseFactory,
    # Backward compatibility
    JudgeResponse,
    JudgeResponseWithTask,
    MissingRequirementsResult,
    ObstacleResult,
    TaskAnalysisResult,
    TaskCompletionResult,
)
from .task_metadata import RequirementsVersion, TaskMetadata, TaskState

__all__ = [
    "DynamicSchemaUserVars",
    "ElicitationFallbackUserVars",
    "EnhancedResponseFactory",
    "JudgeCodeChangeUserVars",
    "JudgeCodingPlanUserVars",
    "JudgeResponse",
    "JudgeResponseWithTask",
    "MissingRequirementsResult",
    "ObstacleResult",
    "RequirementsVersion",
    "ResearchAspect",
    "ResearchAspectsExtraction",
    "ResearchAspectsUserVars",
    "ResearchComplexityFactors",
    "ResearchRequirementsAnalysis",
    "ResearchRequirementsAnalysisUserVars",
    "ResearchValidationResponse",
    "ResearchValidationUserVars",
    "SystemVars",
    "TaskAnalysisResult",
    "TaskCompletionResult",
    "TaskMetadata",
    "TaskState",
    "TestOutputValidationResponse",
    "TestOutputValidationUserVars",
    "URLValidationResult",
    "ValidationErrorUserVars",
    "WorkflowGuidance",
    "WorkflowGuidanceUserVars",
]

# Stubs to satisfy static type checking; real implementations are assigned below.


class SystemVars(BaseModel):
    response_schema: str = Field(default="")
    max_tokens: int = Field(default=0)
    task_size_definitions: str = Field(default="")
    plan_input_schema: str = Field(default="")
    plan_evaluation_criteria: str = Field(default="")
    workflow_guidance: str = Field(default="")
    plan_required_fields_json: str = Field(default="[]")


class DynamicSchemaUserVars(BaseModel):
    context: str
    information_needed: str
    current_understanding: str


class ValidationErrorUserVars(BaseModel):
    validation_issue: str
    context: str


class TestOutputValidationResponse(BaseModel):
    looks_like_test_output: bool = Field(default=False)
    test_framework_detected: str = Field(default="")
    has_test_results: bool = Field(default=False)
    has_execution_summary: bool = Field(default=False)
    confidence_score: float = Field(default=0.0)
    issues: list[str] = Field(default_factory=list)
    feedback: str = Field(default="")


class TestOutputValidationUserVars(BaseModel):
    test_output: str
    context: str


# JudgeCodingPlanUserVars is imported from models.py (see _NAMES list below)
# Type stub for mypy - the actual class is imported dynamically below
if TYPE_CHECKING:
    # Forward declaration for mypy with all fields from models.py
    class DesignPattern(BaseModel):
        name: str
        area: str

    class JudgeCodingPlanUserVars(BaseModel):
        user_requirements: str
        context: str
        plan: str
        design: str
        research: str
        research_urls: list[str] = Field(default_factory=list)
        conversation_history: list[_Any] = Field(default_factory=list)
        problem_domain: str = ""
        problem_non_goals: list[str] = Field(default_factory=list)
        library_plan: list[dict[str, _Any]] = Field(default_factory=list)
        internal_reuse_components: list[dict[str, _Any]] = Field(default_factory=list)
        research_required: bool = False
        research_scope: str = "none"
        research_rationale: str = ""
        internal_research_required: bool = False
        related_code_snippets: list[str] = Field(default_factory=list)
        risk_assessment_required: bool = False
        identified_risks: list[str] = Field(default_factory=list)
        risk_mitigation_strategies: list[str] = Field(default_factory=list)
        expected_url_count: int = 0
        minimum_url_count: int = 0
        url_requirement_reasoning: str = ""
        design_patterns: list[DesignPattern] = Field(default_factory=list)

    conversation_history: list[_Any] = Field(default_factory=list)
    # Conditional research fields
    research_required: bool = False
    research_scope: str = "none"
    research_rationale: str = ""
    # Conditional internal research fields
    internal_research_required: bool = False
    related_code_snippets: list[str] = Field(default_factory=list)
    # Conditional risk assessment fields
    risk_assessment_required: bool = False
    identified_risks: list[str] = Field(default_factory=list)
    risk_mitigation_strategies: list[str] = Field(default_factory=list)


class JudgeCodeChangeUserVars(BaseModel):
    user_requirements: str
    file_path: str
    change_description: str
    code_change: str
    context: str
    conversation_history: list[_Any] = Field(default_factory=list)


class ElicitationFallbackUserVars(BaseModel):
    original_message: str
    required_fields: list[str]
    optional_fields: list[str]


class ResearchValidationUserVars(BaseModel):
    user_requirements: str
    plan: str
    design: str
    research: str
    research_urls: list[str] = Field(default_factory=list)
    context: str
    conversation_history: list[_Any] = Field(default_factory=list)


class TestingEvaluationUserVars(BaseModel):
    user_requirements: str
    task_description: str
    modified_files: list[str] = Field(default_factory=list)
    test_summary: str
    test_files: list[str] = Field(default_factory=list)
    test_execution_results: str
    test_coverage_report: str
    test_types_implemented: list[str] = Field(default_factory=list)
    testing_framework: str
    performance_test_results: str
    manual_test_notes: str
    conversation_history: list[_Any] = Field(default_factory=list)


class ResearchValidationResponse(BaseModel):
    research_adequate: bool
    design_based_on_research: bool
    issues: list[str] = Field(default_factory=list)
    feedback: str


class WorkflowGuidanceUserVars(BaseModel):
    task_id: str
    task_title: str
    task_description: str
    user_requirements: str
    current_state: str
    state_description: str
    current_operation: str
    task_size: str
    task_size_definitions: str
    state_transitions: str
    tool_descriptions: str
    conversation_context: str
    operation_context: str
    response_schema: str


# Placeholders for research-related models if models.py is unavailable
class ResearchComplexityFactors(BaseModel):
    domain_specialization: str = Field(default="general")
    technology_maturity: str = Field(default="established")
    integration_scope: str = Field(default="moderate")
    existing_solutions: str = Field(default="limited")
    risk_level: str = Field(default="medium")


class ResearchRequirementsAnalysis(BaseModel):
    expected_url_count: int = Field(default=3)
    minimum_url_count: int = Field(default=1)
    reasoning: str = Field(default="Fallback analysis")
    complexity_factors: _Any = Field(default=None)
    quality_requirements: list[str] = Field(default_factory=list)


class ResearchRequirementsAnalysisUserVars(BaseModel):
    task_title: str
    task_description: str
    user_requirements: str
    research_scope: str
    research_rationale: str
    context: str


class URLValidationResult(BaseModel):
    adequate: bool = Field(default=False)
    provided_count: int = Field(default=0)
    expected_count: int = Field(default=0)
    minimum_count: int = Field(default=0)
    feedback: str = Field(default="Fallback validation")
    meets_quality_standards: bool = Field(default=False)


def _load_models_py() -> _Any | None:
    current_dir = os.path.dirname(__file__)
    models_py_path = os.path.join(os.path.dirname(current_dir), "models.py")
    if not os.path.exists(models_py_path):
        return None
    spec = importlib.util.spec_from_file_location("models_py", models_py_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


models_py = _load_models_py()

# Names to re-export from models.py
_NAMES = [
    "DesignPattern",
    "ElicitationFallbackUserVars",
    "JudgeCodeChangeUserVars",
    "JudgeCodingPlanUserVars",
    "ResearchValidationResponse",
    "ResearchValidationUserVars",
    "ResearchAspect",
    "ResearchAspectsExtraction",
    "ResearchAspectsUserVars",
    "WorkflowGuidanceUserVars",
    "DynamicSchemaUserVars",
    "ValidationErrorUserVars",
    "SystemVars",
    "ResearchComplexityFactors",
    "ResearchRequirementsAnalysis",
    "ResearchRequirementsAnalysisUserVars",
    "URLValidationResult",
]

for _name in _NAMES:
    if models_py is not None and hasattr(models_py, _name):
        globals()[_name] = getattr(models_py, _name)
    else:
        # Minimal, safe placeholders only used if models.py cannot be loaded
        if _name in {
            "ResearchComplexityFactors",
            "ResearchRequirementsAnalysis",
            "URLValidationResult",
        }:
            # Provide slightly richer defaults for research-related types
            if _name == "ResearchComplexityFactors":

                class ResearchComplexityFactors(BaseModel):  # type: ignore[no-redef]
                    domain_specialization: str = Field(default="general")
                    technology_maturity: str = Field(default="established")
                    integration_scope: str = Field(default="moderate")
                    existing_solutions: str = Field(default="limited")
                    risk_level: str = Field(default="medium")

                globals()[_name] = ResearchComplexityFactors
            elif _name == "ResearchRequirementsAnalysis":

                class ResearchRequirementsAnalysis(BaseModel):  # type: ignore[no-redef]
                    expected_url_count: int = Field(default=3)
                    minimum_url_count: int = Field(default=1)
                    reasoning: str = Field(default="Fallback analysis")
                    complexity_factors: _Any = Field(default=None)
                    quality_requirements: list[str] = Field(default_factory=list)

                globals()[_name] = ResearchRequirementsAnalysis
            else:  # URLValidationResult

                class URLValidationResult(BaseModel):  # type: ignore[no-redef]
                    adequate: bool = Field(default=False)
                    provided_count: int = Field(default=0)
                    expected_count: int = Field(default=0)
                    minimum_count: int = Field(default=0)
                    feedback: str = Field(default="Fallback validation")
                    meets_quality_standards: bool = Field(default=False)

                globals()[_name] = URLValidationResult
        else:
            # Generic placeholder
            globals()[_name] = type(_name, (BaseModel,), {})

"""
Models package for MCP as a Judge.

This package re-exports models for convenient `from mcp_as_a_judge.models import ...`
usage. The canonical `WorkflowGuidance` lives in `workflow/workflow_guidance.py` and
is imported here for a single source of truth.
"""

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
    "URLValidationResult",
    "ValidationErrorUserVars",
    "WorkflowGuidance",
    "WorkflowGuidanceUserVars",
]

# Import additional models from the file `src/mcp_as_a_judge/models.py`.
# We use a lightweight file-based import to avoid the Python package/module name
# collision and keep downstream imports stable.
import importlib.util
import os
from typing import Any

from pydantic import BaseModel, Field


def _load_models_py() -> Any | None:
    current_dir = os.path.dirname(__file__)
    models_py_path = os.path.join(os.path.dirname(current_dir), "models.py")
    if not os.path.exists(models_py_path):
        return None
    spec = importlib.util.spec_from_file_location("models_py", models_py_path)
    if spec is None or spec.loader is None:  # type: ignore[truthy-function]
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


models_py = _load_models_py()

# Names to re-export from models.py
_NAMES = [
    "ElicitationFallbackUserVars",
    "JudgeCodeChangeUserVars",
    "JudgeCodingPlanUserVars",
    "ResearchValidationResponse",
    "ResearchValidationUserVars",
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
                    complexity_factors: Any = Field(default=None)
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

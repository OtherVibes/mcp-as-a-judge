"""
Models package for MCP as a Judge.

This package contains all data models used throughout the application,
including task metadata, enhanced responses, and workflow guidance models.
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
    "DynamicSchemaSystemVars",
    "ElicitationFallbackUserVars",
    "EnhancedResponseFactory",
    "JudgeCodeChangeSystemVars",
    "JudgeCodeChangeUserVars",
    "JudgeCodingPlanSystemVars",
    "JudgeCodingPlanUserVars",
    "JudgeResponse",
    "JudgeResponseWithTask",
    "MissingRequirementsResult",
    "ObstacleResult",
    "RequirementsVersion",
    "ResearchComplexityFactors",
    "ResearchRequirementsAnalysis",
    "ResearchRequirementsAnalysisSystemVars",
    "ResearchRequirementsAnalysisUserVars",
    "ResearchValidationResponse",
    "ResearchValidationSystemVars",
    "ResearchValidationUserVars",
    "TaskAnalysisResult",
    "TaskCompletionResult",
    "TaskMetadata",
    "TaskState",
    "URLValidationResult",
    "WorkflowGuidance",
    "WorkflowGuidanceSystemVars",
    "WorkflowGuidanceUserVars",
]

# Import additional models from the original models.py file
# Import them here to avoid circular imports
try:
    import importlib.util
    import os

    # Get the path to models.py
    current_dir = os.path.dirname(__file__)
    models_py_path = os.path.join(os.path.dirname(current_dir), "models.py")

    if os.path.exists(models_py_path):
        spec = importlib.util.spec_from_file_location("models_py", models_py_path)
        if spec is not None:
            models_py = importlib.util.module_from_spec(spec)
            if spec.loader is not None:
                spec.loader.exec_module(models_py)  # type: ignore[union-attr]

        # Import the models we need
        ElicitationFallbackUserVars = models_py.ElicitationFallbackUserVars
        JudgeCodeChangeSystemVars = models_py.JudgeCodeChangeSystemVars
        JudgeCodeChangeUserVars = models_py.JudgeCodeChangeUserVars
        JudgeCodingPlanSystemVars = models_py.JudgeCodingPlanSystemVars
        JudgeCodingPlanUserVars = models_py.JudgeCodingPlanUserVars
        ResearchValidationResponse = models_py.ResearchValidationResponse
        ResearchValidationSystemVars = models_py.ResearchValidationSystemVars
        ResearchValidationUserVars = models_py.ResearchValidationUserVars
        WorkflowGuidanceSystemVars = models_py.WorkflowGuidanceSystemVars
        WorkflowGuidanceUserVars = models_py.WorkflowGuidanceUserVars
        DynamicSchemaSystemVars = models_py.DynamicSchemaSystemVars
        DynamicSchemaUserVars = models_py.DynamicSchemaUserVars

        # Import research-related models
        ResearchComplexityFactors = models_py.ResearchComplexityFactors
        ResearchRequirementsAnalysis = models_py.ResearchRequirementsAnalysis
        ResearchRequirementsAnalysisSystemVars = (
            models_py.ResearchRequirementsAnalysisSystemVars
        )
        ResearchRequirementsAnalysisUserVars = (
            models_py.ResearchRequirementsAnalysisUserVars
        )
        URLValidationResult = models_py.URLValidationResult

except Exception:
    # Fallback if models.py doesn't exist or has issues
    # Create minimal fallback classes to prevent import errors
    from pydantic import BaseModel, Field

    class ElicitationFallbackUserVars(BaseModel):
        pass

    class JudgeCodeChangeSystemVars(BaseModel):
        pass

    class JudgeCodeChangeUserVars(BaseModel):
        pass

    class JudgeCodingPlanSystemVars(BaseModel):
        pass

    class JudgeCodingPlanUserVars(BaseModel):
        pass

    class ResearchValidationResponse(BaseModel):
        pass

    class ResearchValidationSystemVars(BaseModel):
        pass

    class ResearchValidationUserVars(BaseModel):
        pass

    class WorkflowGuidanceSystemVars(BaseModel):
        pass

    class WorkflowGuidanceUserVars(BaseModel):
        pass

    class DynamicSchemaSystemVars(BaseModel):
        pass

    class DynamicSchemaUserVars(BaseModel):
        pass

    class ResearchComplexityFactors(BaseModel):
        domain_specialization: str = Field(default="general")
        technology_maturity: str = Field(default="established")
        integration_scope: str = Field(default="moderate")
        existing_solutions: str = Field(default="limited")
        risk_level: str = Field(default="medium")

    class ResearchRequirementsAnalysis(BaseModel):
        expected_url_count: int = Field(default=3)
        minimum_url_count: int = Field(default=2)
        reasoning: str = Field(default="Fallback analysis")
        complexity_factors: ResearchComplexityFactors = Field(
            default_factory=ResearchComplexityFactors
        )
        quality_requirements: list[str] = Field(default_factory=list)

    class ResearchRequirementsAnalysisSystemVars(BaseModel):
        pass

    class ResearchRequirementsAnalysisUserVars(BaseModel):
        pass

    class URLValidationResult(BaseModel):
        adequate: bool = Field(default=False)
        provided_count: int = Field(default=0)
        expected_count: int = Field(default=3)
        minimum_count: int = Field(default=2)
        feedback: str = Field(default="Fallback validation")
        meets_quality_standards: bool = Field(default=False)

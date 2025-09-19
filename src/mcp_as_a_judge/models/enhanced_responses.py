from typing import Any

from pydantic import BaseModel, Field, model_serializer

from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskSize
from mcp_as_a_judge.workflow.workflow_guidance import WorkflowGuidance


class TrimmedBaseModel(BaseModel):
    @model_serializer(mode="wrap")
    def _serialize_trimmed(self, serializer: Any) -> dict:
        # Common Pydantic v2 approach: exclude unset, None, and defaults
        # This drops nulls and empty containers that are at their defaults.
        try:
            data = serializer(
                self,
                mode="json",
                exclude_unset=True,
                exclude_none=True,
                exclude_defaults=True,
            )
        except TypeError:
            data = serializer(self)
        return data or {}


class JudgeResponse(TrimmedBaseModel):
    approved: bool = Field(description="Whether the validation passed")
    required_improvements: list[str] = Field(
        default_factory=list,
        description="List of required improvements if not approved",
    )
    feedback: str = Field(description="Detailed feedback about the validation")

    # Optional unified Git diff with suggested fixes or refinements
    suggested_diff: str | None = Field(
        default=None,
        description=(
            "Unified Git diff patch with suggested changes (optional). "
            "Provide when rejecting with concrete fixes or when proposing minor refinements."
        ),
    )

    class FileReview(TrimmedBaseModel):
        path: str = Field(description="File path reviewed")
        feedback: str = Field(description="Per-file feedback summary")
        approved: bool | None = Field(
            default=None, description="Optional per-file approval or risk flag"
        )

    reviewed_files: list[FileReview] = Field(
        default_factory=list,
        description=(
            "Per-file reviews. Must include an entry for every file changed in the diff."
        ),
    )

    current_task_metadata: TaskMetadata = Field(
        default_factory=lambda: TaskMetadata(
            title="Unknown Task",
            description="No metadata provided",
            user_requirements="",
            task_size=TaskSize.M,
        ),
        description="ALWAYS current state of task metadata after operation",
    )
    workflow_guidance: WorkflowGuidance = Field(
        default_factory=lambda: WorkflowGuidance(
            next_tool="raise_obstacle",
            reasoning="Default guidance: insufficient context",
            preparation_needed=[],
            guidance="Provide required parameters and context",
        ),
        description="LLM-generated next steps and instructions from shared method",
    )


class TaskAnalysisResult(TrimmedBaseModel):
    action: str = Field(description="Action taken: 'created' or 'updated'")
    context_summary: str = Field(
        description="Summary of the task context and current state"
    )

    current_task_metadata: TaskMetadata = Field(
        description="ALWAYS current state of task metadata after operation"
    )
    workflow_guidance: WorkflowGuidance = Field(
        description="LLM-generated next steps and instructions from shared method"
    )


class TaskCompletionResult(TrimmedBaseModel):
    approved: bool = Field(description="Whether the task completion is approved")
    feedback: str = Field(
        description="Detailed feedback about the completion validation"
    )
    required_improvements: list[str] = Field(
        default_factory=list,
        description="List of required improvements if not approved",
    )
    current_task_metadata: TaskMetadata = Field(
        description="ALWAYS current state of task metadata after operation"
    )
    workflow_guidance: WorkflowGuidance = Field(
        description="LLM-generated next steps and instructions (or workflow complete)"
    )


class ObstacleResult(TrimmedBaseModel):
    obstacle_acknowledged: bool = Field(
        description="Whether the obstacle has been acknowledged"
    )
    resolution_guidance: str = Field(description="Guidance for resolving the obstacle")
    alternative_approaches: list[str] = Field(
        default_factory=list, description="Alternative approaches to consider"
    )
    current_task_metadata: TaskMetadata = Field(
        description="ALWAYS current state of task metadata after operation"
    )
    workflow_guidance: WorkflowGuidance = Field(
        description="LLM-generated next steps and instructions for obstacle resolution"
    )


class MissingRequirementsResult(TrimmedBaseModel):
    clarification_needed: bool = Field(description="Whether clarification is needed")
    missing_information: list[str] = Field(
        default_factory=list,
        description="List of missing information that needs clarification",
    )
    clarification_questions: list[str] = Field(
        default_factory=list, description="Specific questions to ask for clarification"
    )
    current_task_metadata: TaskMetadata = Field(
        description="ALWAYS current state of task metadata after operation"
    )
    workflow_guidance: WorkflowGuidance = Field(
        description="LLM-generated next steps and instructions for requirements clarification"
    )


# Backward compatibility alias
JudgeResponseWithTask = JudgeResponse


class EnhancedResponseFactory:
    @staticmethod
    def create_judge_response(
        approved: bool,
        feedback: str,
        current_task_metadata: TaskMetadata,
        workflow_guidance: WorkflowGuidance,
        required_improvements: list[str] | None = None,
    ) -> JudgeResponse:
        return JudgeResponse(
            approved=approved,
            feedback=feedback,
            required_improvements=required_improvements or [],
            current_task_metadata=current_task_metadata,
            workflow_guidance=workflow_guidance,
        )

    @staticmethod
    def create_task_analysis_result(
        action: str,
        context_summary: str,
        current_task_metadata: TaskMetadata,
        workflow_guidance: WorkflowGuidance,
    ) -> TaskAnalysisResult:
        return TaskAnalysisResult(
            action=action,
            context_summary=context_summary,
            current_task_metadata=current_task_metadata,
            workflow_guidance=workflow_guidance,
        )

    @staticmethod
    def create_task_completion_result(
        approved: bool,
        feedback: str,
        current_task_metadata: TaskMetadata,
        workflow_guidance: WorkflowGuidance,
        required_improvements: list[str] | None = None,
    ) -> TaskCompletionResult:
        return TaskCompletionResult(
            approved=approved,
            feedback=feedback,
            required_improvements=required_improvements or [],
            current_task_metadata=current_task_metadata,
            workflow_guidance=workflow_guidance,
        )


class ElicitationResult(TrimmedBaseModel):
    """Result from user requirement elicitation."""

    success: bool = Field(description="Whether elicitation was successful")
    clarified_requirements: str = Field(
        default="", description="Updated requirements based on user input"
    )
    technical_decisions: dict[str, str] = Field(
        default_factory=dict, description="Technical decisions made by user"
    )
    user_responses: dict[str, str] = Field(
        default_factory=dict, description="Raw user responses to questions"
    )
    repository_context: str = Field(
        default="", description="Repository analysis that informed decisions"
    )
    workflow_impact: str = Field(
        default="", description="How user input affects workflow and tool selection"
    )
    error_message: str = Field(
        default="", description="Error message if elicitation failed"
    )


class PlanCreationResult(TrimmedBaseModel):
    """Result from LLM-powered implementation plan creation."""

    success: bool = Field(description="Whether plan creation was successful")
    plan: str = Field(default="", description="Detailed implementation plan")
    design: str = Field(default="", description="System design and architecture")
    research: str = Field(
        default="", description="Research findings and best practices"
    )
    technical_decisions: list[dict] = Field(
        default_factory=list, description="Technical decisions made during planning"
    )
    implementation_scope: dict = Field(
        default_factory=dict, description="Scope breakdown with files and complexity"
    )
    language_specific_practices: list[str] = Field(
        default_factory=list, description="Best practices for chosen technology stack"
    )
    risk_assessment: str = Field(
        default="", description="Potential risks and mitigation strategies"
    )
    error_message: str = Field(
        default="", description="Error message if plan creation failed"
    )


class PlanUpdateResult(TrimmedBaseModel):
    """Result from updating plan based on LLM feedback."""

    success: bool = Field(description="Whether plan update was successful")
    updated_plan: str = Field(default="", description="Updated implementation plan")
    updated_design: str = Field(
        default="", description="Updated system design and architecture"
    )
    updated_research: str = Field(
        default="", description="Updated research findings and best practices"
    )
    llm_improvements: list[str] = Field(
        default_factory=list, description="List of improvements made by LLM"
    )
    technical_changes: list[dict] = Field(
        default_factory=list, description="Technical changes made to the plan"
    )
    change_rationale: str = Field(
        default="", description="Explanation of why changes were made"
    )
    version_info: str = Field(
        default="",
        description="Plan version information (e.g., 'Plan B based on LLM feedback')",
    )
    error_message: str = Field(
        default="", description="Error message if plan update failed"
    )


class PlanApprovalResult(TrimmedBaseModel):
    """Result from user plan approval."""

    approved: bool = Field(description="Whether user approved the plan")
    user_feedback: str = Field(default="", description="User feedback on the plan")
    requirement_updates: str = Field(
        default="", description="Updates to requirements based on user feedback"
    )
    plan_modifications: list[str] = Field(
        default_factory=list, description="Specific plan modifications requested"
    )
    technical_concerns: list[str] = Field(
        default_factory=list, description="Technical concerns raised by user"
    )
    workflow_changes: str = Field(
        default="", description="How approval/feedback affects next steps"
    )
    error_message: str = Field(
        default="", description="Error message if approval process failed"
    )

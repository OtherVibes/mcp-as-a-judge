"""
Enhanced response models for workflow v3.

This module defines the response models that all enhanced workflow tools return,
incorporating TaskMetadata and WorkflowGuidance for consistent task tracking
and intelligent next-step guidance.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskSize
from mcp_as_a_judge.workflow.workflow_guidance import WorkflowGuidance


class JudgeResponse(BaseModel):
    """
    Enhanced JudgeResponse that ALWAYS includes current task metadata and workflow guidance.
    
    This model extends the standard judge response to include task tracking
    and intelligent next-step guidance for the enhanced workflow v3 system.
    """
    # Standard JudgeResponse fields
    approved: bool = Field(
        description="Whether the validation passed"
    )
    required_improvements: List[str] = Field(
        default_factory=list,
        description="List of required improvements if not approved"
    )
    feedback: str = Field(
        description="Detailed feedback about the validation"
    )
    
    # Enhanced workflow v3 fields
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


class TaskAnalysisResult(BaseModel):
    """
    Result of coding task analysis from set_coding_task.
    
    This model is returned when creating or updating coding tasks,
    providing context about the action taken and guidance for next steps.
    """
    action: str = Field(
        description="Action taken: 'created' or 'updated'"
    )
    context_summary: str = Field(
        description="Summary of the task context and current state"
    )
    
    # Enhanced workflow v3 fields
    current_task_metadata: TaskMetadata = Field(
        description="ALWAYS current state of task metadata after operation"
    )
    workflow_guidance: WorkflowGuidance = Field(
        description="LLM-generated next steps and instructions from shared method"
    )


class TaskCompletionResult(BaseModel):
    """
    Coding task completion result with current metadata and workflow guidance.
    
    This model is returned by judge_task_completion to indicate whether
    the coding task has been successfully completed and what to do next.
    """
    # Completion validation fields
    approved: bool = Field(
        description="Whether the task completion is approved"
    )
    feedback: str = Field(
        description="Detailed feedback about the completion validation"
    )
    required_improvements: List[str] = Field(
        default_factory=list,
        description="List of required improvements if not approved"
    )
    
    # Enhanced workflow v3 fields
    current_task_metadata: TaskMetadata = Field(
        description="ALWAYS current state of task metadata after operation"
    )
    workflow_guidance: WorkflowGuidance = Field(
        description="LLM-generated next steps and instructions (or workflow complete)"
    )


class ObstacleResult(BaseModel):
    """
    Result from raise_obstacle tool with task metadata and workflow guidance.
    
    This model is returned when an obstacle prevents task completion,
    providing context about the obstacle and guidance for resolution.
    """
    # Obstacle information
    obstacle_acknowledged: bool = Field(
        description="Whether the obstacle has been acknowledged"
    )
    resolution_guidance: str = Field(
        description="Guidance for resolving the obstacle"
    )
    alternative_approaches: List[str] = Field(
        default_factory=list,
        description="Alternative approaches to consider"
    )
    
    # Enhanced workflow v3 fields
    current_task_metadata: TaskMetadata = Field(
        description="ALWAYS current state of task metadata after operation"
    )
    workflow_guidance: WorkflowGuidance = Field(
        description="LLM-generated next steps and instructions for obstacle resolution"
    )


class MissingRequirementsResult(BaseModel):
    """
    Result from raise_missing_requirements tool with task metadata and workflow guidance.
    
    This model is returned when requirements are unclear or incomplete,
    providing context about what's missing and guidance for clarification.
    """
    # Requirements clarification information
    clarification_needed: bool = Field(
        description="Whether clarification is needed"
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="List of missing information that needs clarification"
    )
    clarification_questions: List[str] = Field(
        default_factory=list,
        description="Specific questions to ask for clarification"
    )
    
    # Enhanced workflow v3 fields
    current_task_metadata: TaskMetadata = Field(
        description="ALWAYS current state of task metadata after operation"
    )
    workflow_guidance: WorkflowGuidance = Field(
        description="LLM-generated next steps and instructions for requirements clarification"
    )

# Backward compatibility alias
JudgeResponseWithTask = JudgeResponse


class EnhancedResponseFactory:
    """
    Factory for creating enhanced response models with consistent task metadata.
    
    This factory ensures that all enhanced responses include current task metadata
    and workflow guidance, providing a consistent interface for tool responses.
    """
    
    @staticmethod
    def create_judge_response(
        approved: bool,
        feedback: str,
        current_task_metadata: TaskMetadata,
        workflow_guidance: WorkflowGuidance,
        required_improvements: Optional[List[str]] = None,
    ) -> JudgeResponse:
        """
        Create a JudgeResponse with consistent structure.
        
        Args:
            approved: Whether the validation passed
            feedback: Detailed feedback about the validation
            current_task_metadata: Current state of task metadata
            workflow_guidance: LLM-generated workflow guidance
            required_improvements: Optional list of required improvements
            
        Returns:
            JudgeResponse instance
        """
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
        """
        Create a TaskAnalysisResult with consistent structure.
        
        Args:
            action: Action taken ('created' or 'updated')
            context_summary: Summary of the task context
            current_task_metadata: Current state of task metadata
            workflow_guidance: LLM-generated workflow guidance
            
        Returns:
            TaskAnalysisResult instance
        """
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
        required_improvements: Optional[List[str]] = None,
    ) -> TaskCompletionResult:
        """
        Create a TaskCompletionResult with consistent structure.
        
        Args:
            approved: Whether the task completion is approved
            feedback: Detailed feedback about completion
            current_task_metadata: Current state of task metadata
            workflow_guidance: LLM-generated workflow guidance
            required_improvements: Optional list of required improvements
            
        Returns:
            TaskCompletionResult instance
        """
        return TaskCompletionResult(
            approved=approved,
            feedback=feedback,
            required_improvements=required_improvements or [],
            current_task_metadata=current_task_metadata,
            workflow_guidance=workflow_guidance,
        )

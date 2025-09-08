"""
Task metadata models for coding task workflow.

This module defines the core TaskMetadata model and TaskState enum that form
the foundation of the enhanced workflow v3 system.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TaskState(str, Enum):
    """
    Coding task state enum with well-documented transitions.
    
    State Transitions:
    - CREATED → PLANNING: Task created, ready for planning phase
    - PLANNING → PLAN_APPROVED: Plan validated and approved
    - PLAN_APPROVED → IMPLEMENTING: Implementation phase started
    - IMPLEMENTING → IMPLEMENTING: Multiple code changes during implementation
    - IMPLEMENTING → TESTING: Implementation complete, ready for testing
    - TESTING → TESTING: Multiple test iterations
    - TESTING → REVIEW_READY: All tests passing, ready for final review
    - REVIEW_READY → COMPLETED: Task completed successfully
    - Any state → BLOCKED: Task blocked by external dependencies
    - Any state → CANCELLED: Task cancelled
    - BLOCKED → Previous state: Unblocked, return to previous state
    
    Usage:
    - CREATED: Default state for new tasks, needs planning
    - PLANNING: Planning phase in progress (set when planning starts)
    - PLAN_APPROVED: Plan validated and approved (set by judge_coding_plan)
    - IMPLEMENTING: Implementation phase in progress (set when coding starts)
    - TESTING: Testing phase in progress (set when implementation complete)
    - REVIEW_READY: All tests passing, ready for final review
    - COMPLETED: Task completed successfully (set by judge_task_completion)
    - BLOCKED: Task blocked by external dependencies (manual override)
    - CANCELLED: Task cancelled (manual override)
    """
    CREATED = "created"              # Task just created, needs planning
    PLANNING = "planning"            # Planning phase in progress
    PLAN_APPROVED = "plan_approved"  # Plan validated and approved
    IMPLEMENTING = "implementing"    # Implementation phase in progress
    TESTING = "testing"              # Testing phase in progress
    REVIEW_READY = "review_ready"    # All tests passing, ready for final review
    COMPLETED = "completed"          # Task completed successfully
    BLOCKED = "blocked"              # Task blocked by external dependencies
    CANCELLED = "cancelled"          # Task cancelled


class RequirementsVersion(BaseModel):
    """A version of user requirements with timestamp and source."""
    content: str
    source: str  # "initial", "clarification", "update"
    timestamp: datetime = Field(default_factory=datetime.now)


class TaskMetadata(BaseModel):
    """
    Lightweight metadata for coding tasks that flows with memory layer.
    
    This model serves as the foundation for the enhanced workflow v3 system,
    replacing session-based tracking with task-centric approach.
    """
    
    # IMMUTABLE FIELDS - Never change after creation
    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="IMMUTABLE: Auto-generated UUID, primary key for memory storage"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="IMMUTABLE: Task creation timestamp"
    )
    
    # MUTABLE FIELDS - Can be updated via set_coding_task
    name: str = Field(
        description="Human-readable slug for coding task (updatable)"
    )
    title: str = Field(
        description="Display title for coding task (updatable)"
    )
    description: str = Field(
        description="Detailed coding task description (updatable)"
    )
    user_requirements: str = Field(
        default="",
        description="Current coding requirements (updatable)"
    )
    state: TaskState = Field(
        default=TaskState.CREATED,
        description="Current task state (updatable, follows TaskState transitions)"
    )
    
    # SYSTEM MANAGED FIELDS - Updated by system, not directly by user
    user_requirements_history: List[RequirementsVersion] = Field(
        default_factory=list,
        description="History of requirements changes"
    )
    accumulated_diff: Dict[str, Any] = Field(
        default_factory=dict,
        description="Code changes accumulated over time"
    )
    modified_files: List[str] = Field(
        default_factory=list,
        description="List of file paths that were created or modified during task implementation"
    )
    test_files: List[str] = Field(
        default_factory=list,
        description="List of test file paths that were created during testing phase"
    )
    test_status: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of different test types (unit, integration, e2e, etc.)"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Coding-related tags"
    )
    
    def update_requirements(self, new_requirements: str, source: str = "update") -> None:
        """
        Update user requirements and add to history.
        
        Args:
            new_requirements: New requirements text
            source: Source of the update ("initial", "clarification", "update")
        """
        if self.user_requirements != new_requirements:
            # Add current requirements to history before updating
            if self.user_requirements:
                version = RequirementsVersion(
                    content=self.user_requirements,
                    source="previous",
                    timestamp=self.updated_at
                )
                self.user_requirements_history.append(version)
            
            # Update current requirements
            self.user_requirements = new_requirements
            self.updated_at = datetime.now()
            
            # Add new version to history
            new_version = RequirementsVersion(
                content=new_requirements,
                source=source,
                timestamp=self.updated_at
            )
            self.user_requirements_history.append(new_version)

    def add_modified_file(self, file_path: str) -> None:
        """
        Add a file to the list of modified files during task implementation.

        Args:
            file_path: Path to the file that was created or modified
        """
        if file_path not in self.modified_files:
            self.modified_files.append(file_path)
            self.updated_at = datetime.now()

    def add_test_file(self, test_file_path: str) -> None:
        """
        Add a test file to the list of test files created during testing.

        Args:
            test_file_path: Path to the test file that was created
        """
        if test_file_path not in self.test_files:
            self.test_files.append(test_file_path)
            self.updated_at = datetime.now()

    def update_test_status(self, test_type: str, status: str) -> None:
        """
        Update the status of a specific test type.

        Args:
            test_type: Type of test (unit, integration, e2e, etc.)
            status: Status (passing, failing, not_implemented, etc.)
        """
        self.test_status[test_type] = status
        self.updated_at = datetime.now()

    def get_test_coverage_summary(self) -> Dict[str, Any]:
        """
        Get a summary of test coverage and status.

        Returns:
            Dictionary with test coverage information
        """
        return {
            "test_files_count": len(self.test_files),
            "test_files": self.test_files,
            "test_status": self.test_status,
            "has_tests": len(self.test_files) > 0,
            "all_tests_passing": all(status == "passing" for status in self.test_status.values()) if self.test_status else False,
        }

    def update_state(self, new_state: TaskState) -> None:
        """
        Update task state and timestamp.
        
        Args:
            new_state: New TaskState value
        """
        if self.state != new_state:
            self.state = new_state
            self.updated_at = datetime.now()
    
    def add_accumulated_change(self, file_path: str, change_data: Dict[str, Any]) -> None:
        """
        Add a code change to the accumulated diff.
        
        Args:
            file_path: Path to the file that was changed
            change_data: Dictionary containing change information
        """
        if file_path not in self.accumulated_diff:
            self.accumulated_diff[file_path] = []
        
        change_entry = {
            **change_data,
            "timestamp": datetime.now().isoformat()
        }
        self.accumulated_diff[file_path].append(change_entry)
        self.updated_at = datetime.now()
    
    def get_current_state_info(self) -> Dict[str, str]:
        """
        Get human-readable information about current state.
        
        Returns:
            Dictionary with state info and next expected actions
        """
        state_info = {
            TaskState.CREATED: {
                "description": "Task created, ready for planning",
                "next_action": "Create detailed implementation plan with code analysis"
            },
            TaskState.PLANNING: {
                "description": "Planning phase in progress",
                "next_action": "Complete and validate implementation plan"
            },
            TaskState.PLAN_APPROVED: {
                "description": "Plan approved, ready for implementation",
                "next_action": "Start implementing code changes"
            },
            TaskState.IMPLEMENTING: {
                "description": "Implementation in progress",
                "next_action": "Continue implementing or transition to testing"
            },
            TaskState.TESTING: {
                "description": "Testing phase in progress",
                "next_action": "Write and run tests, ensure all tests pass"
            },
            TaskState.REVIEW_READY: {
                "description": "All tests passing, ready for final review",
                "next_action": "Validate task completion"
            },
            TaskState.COMPLETED: {
                "description": "Task completed successfully",
                "next_action": "Task is complete"
            },
            TaskState.BLOCKED: {
                "description": "Task blocked by external dependencies",
                "next_action": "Resolve blocking issues"
            },
            TaskState.CANCELLED: {
                "description": "Task cancelled",
                "next_action": "Task is cancelled"
            }
        }
        
        return state_info.get(self.state, {
            "description": f"Unknown state: {self.state}",
            "next_action": "Review task state"
        })

"""
Task metadata models for coding task workflow.

This module defines the core TaskMetadata model and TaskState enum that form
the foundation of the enhanced workflow v3 system.
"""

import time
import uuid
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class TaskSize(str, Enum):
    """
    Task size classification for workflow optimization.

    Sizes are based on estimated complexity and time requirements:
    - XS: Extra Small - Simple fixes, typos, minor config changes (< 30 minutes)
    - S: Small - Minor features, simple refactoring (30 minutes - 2 hours)
    - M: Medium - Standard features, moderate complexity (2-8 hours) - DEFAULT
    - L: Large - Complex features, multiple components (1-3 days)
    - XL: Extra Large - Major system changes, architectural updates (3+ days)

    This classification determines workflow routing:
    - XS/S: Skip planning phase, minimal validation
    - M: Standard workflow (current behavior)
    - L/XL: Enhanced validation, mandatory risk assessment
    """

    XS = "xs"  # Extra Small: Simple fixes, typos (< 30 min)
    S = "s"  # Small: Minor features, simple refactoring (30 min - 2 hours)
    M = "m"  # Medium: Standard features (2-8 hours) - DEFAULT
    L = "l"  # Large: Complex features, multiple components (1-3 days)
    XL = "xl"  # Extra Large: Major system changes (3+ days)


class TaskState(str, Enum):
    """
    Coding task state enum with well-documented transitions.

    State Transitions:
    - CREATED → PLANNING: Task created, ready for planning phase (XS/S may skip to IMPLEMENTING)
    - PLANNING → PLAN_APPROVED: Plan validated and approved
    - PLAN_APPROVED → IMPLEMENTING: Implementation phase started
    - IMPLEMENTING → IMPLEMENTING: Multiple code changes during implementation
    - IMPLEMENTING → REVIEW_READY: Implementation complete, ready for code review
    - REVIEW_READY → TESTING: Code review approved, ready for testing validation
    - TESTING → TESTING: Multiple test iterations
    - TESTING → COMPLETED: All tests validated; task completed successfully
    - Any state → BLOCKED: Task blocked by external dependencies
    - Any state → CANCELLED: Task cancelled
    - BLOCKED → Previous state: Unblocked, return to previous state

    Usage:
    - CREATED: Default state for new tasks, needs planning (XS/S may proceed directly to IMPLEMENTING)
    - PLANNING: Planning phase in progress (set when planning starts)
    - PLAN_APPROVED: Plan validated and approved (set by judge_coding_plan)
    - IMPLEMENTING: Implementation phase in progress (set when coding starts)
    - REVIEW_READY: Implementation complete and ready for code review
    - TESTING: Testing/validation phase after code review approval
    - COMPLETED: Task completed successfully (set by judge_coding_task_completion)
    - BLOCKED: Task blocked by external dependencies (manual override)
    - CANCELLED: Task cancelled (manual override)
    """

    CREATED = "created"  # Task just created, needs planning
    PLANNING = "planning"  # Planning phase in progress
    PLAN_APPROVED = "plan_approved"  # Plan validated and approved
    IMPLEMENTING = "implementing"  # Implementation phase in progress
    TESTING = "testing"  # Testing phase in progress
    REVIEW_READY = "review_ready"  # All tests passing, ready for final review
    COMPLETED = "completed"  # Task completed successfully
    BLOCKED = "blocked"  # Task blocked by external dependencies
    CANCELLED = "cancelled"  # Task cancelled


class ResearchScope(str, Enum):
    """
    Research scope enum for workflow-driven research validation.

    Determines the depth and requirements for research validation:
    - NONE: No research required for this task complexity
    - LIGHT: Light research required (1+ authoritative domain source)
    - DEEP: Deep research required (2+ authoritative domain sources)
    """

    NONE = "none"  # No research required
    LIGHT = "light"  # Light research required
    DEEP = "deep"  # Deep research required


class RequirementsVersion(BaseModel):
    """A version of user requirements with timestamp and source."""

    content: str
    source: str  # "initial", "clarification", "update"
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class TaskMetadata(BaseModel):
    """
    Lightweight metadata for coding tasks that flows with memory layer.

    This model serves as the foundation for the enhanced workflow v3 system,
    replacing session-based tracking with task-centric approach.
    """

    PLAN_REJECTION_LIMIT: ClassVar[int] = 1

    # IMMUTABLE FIELDS - Never change after creation
    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="IMMUTABLE: Auto-generated UUID, primary key for memory storage",
    )
    created_at: int = Field(
        default_factory=lambda: int(time.time()),
        description="IMMUTABLE: Task creation timestamp (epoch seconds)",
    )

    # MUTABLE FIELDS - Can be updated via set_coding_task
    title: str = Field(description="Display title for coding task (updatable)")
    description: str = Field(description="Detailed coding task description (updatable)")
    user_requirements: str = Field(
        default="", description="Current coding requirements (updatable)"
    )
    state: TaskState = Field(
        default=TaskState.CREATED,
        description="Current task state (updatable, follows TaskState transitions)",
    )
    task_size: TaskSize = Field(
        description="Task size classification for workflow optimization (XS=simple fixes, S=minor features, M=standard, L=complex, XL=major changes)"
    )

    # SYSTEM MANAGED FIELDS - Updated by system, not directly by user
    user_requirements_history: list[RequirementsVersion] = Field(
        default_factory=list, description="History of requirements changes"
    )
    accumulated_diff: dict[str, Any] = Field(
        default_factory=dict, description="Code changes accumulated over time"
    )
    modified_files: list[str] = Field(
        default_factory=list,
        description="List of file paths that were created or modified during task implementation",
    )
    test_files: list[str] = Field(
        default_factory=list,
        description="List of test file paths that were created during testing phase",
    )
    test_status: dict[str, str] = Field(
        default_factory=dict,
        description="Status of different test types (unit, integration, e2e, etc.)",
    )
    updated_at: int = Field(
        default_factory=lambda: int(time.time()),
        description="Last update timestamp (epoch seconds)",
    )
    tags: list[str] = Field(default_factory=list, description="Coding-related tags")

    # (No explicit decision ledger; decisions are handled via LLM-driven elicitation and conversation history)

    # PROBLEM DOMAIN & REUSE/DEPENDENCIES PLAN - For enforcing domain focus and avoiding reinvention
    problem_domain: str = Field(
        default="",
        description="Concise statement of the problem domain and scope for this task",
    )
    problem_non_goals: list[str] = Field(
        default_factory=list,
        description="Explicit non-goals/boundaries to prevent scope creep and re-solving commodity concerns",
    )

    class LibraryPlanItem(BaseModel):
        purpose: str = Field(
            description="Non-domain concern or integration point this library addresses"
        )
        selection: str = Field(
            description="Chosen library or internal utility (name and optional version)"
        )
        source: str = Field(
            description="Source of solution: 'internal' for repo utility, 'external' for well-known library, 'custom' for in-house code"
        )
        justification: str = Field(
            default="",
            description="One-line rationale for the selection and any trade-offs",
        )

    library_plan: list[LibraryPlanItem] = Field(
        default_factory=list,
        description=(
            "Planned libraries/utilities per purpose; prefer internal reuse and well-known libraries; custom code only with justification"
        ),
    )

    class ReuseComponent(BaseModel):
        path: str = Field(description="Repository path to the reusable component")
        purpose: str = Field(
            default="",
            description="What part of the task this component will support",
        )
        notes: str = Field(default="", description="Any integration notes or caveats")

    internal_reuse_components: list[ReuseComponent] = Field(
        default_factory=list,
        description="Existing repository components/utilities to reuse with paths and purposes",
    )

    # RESEARCH TRACKING FIELDS - Added for workflow-driven research validation
    research_required: bool | None = Field(
        default=None,
        description="Whether research is required by workflow guidance (None=undetermined, True=required, False=optional)",
    )
    research_scope: ResearchScope = Field(
        default=ResearchScope.NONE,
        description="Research scope determined by workflow: none|light|deep",
    )
    research_completed: int | None = Field(
        default=None, description="Epoch seconds when research validation passed"
    )
    research_rationale: str = Field(
        default="",
        description="Explanation of why research was required and how the scope was determined",
    )

    # DYNAMIC URL REQUIREMENTS - LLM-driven research URL count determination
    expected_url_count: int | None = Field(
        default=None,
        description="LLM-determined expected number of research URLs based on task complexity",
    )
    minimum_url_count: int | None = Field(
        default=None,
        description="LLM-determined minimum acceptable URL count for adequate research",
    )
    url_requirement_reasoning: str = Field(
        default="",
        description="LLM-generated explanation of why specific URL count is needed for this task",
    )
    research_complexity_analysis: dict | None = Field(
        default=None,
        description="Detailed complexity analysis factors from LLM (domain, tech maturity, integration scope, etc.)",
    )

    # INTERNAL RESEARCH FIELDS - For code snippet analysis
    internal_research_required: bool | None = Field(
        default=None,
        description="Whether internal codebase research is needed (None=undetermined, True=required, False=not needed)",
    )
    related_code_snippets: list[str] = Field(
        default_factory=list,
        description="Related code snippets from the codebase that are relevant to this task",
    )

    # RISK ASSESSMENT FIELDS - For identifying potential harm areas
    risk_assessment_required: bool | None = Field(
        default=None,
        description="Whether risk assessment is needed (None=undetermined, True=required, False=not needed)",
    )
    identified_risks: list[str] = Field(
        default_factory=list,
        description="Areas that could be harmed by the proposed changes",
    )
    risk_mitigation_strategies: list[str] = Field(
        default_factory=list, description="Strategies to mitigate identified risks"
    )

    # DESIGN PATTERNS ENFORCEMENT - For tracking if task requires design patterns
    design_patterns_enforcement: bool | None = Field(
        default=None,
        description="Whether design patterns are required for this task (None=undetermined, True=required, False=not needed)",
    )

    # APPROVAL TRACKING FIELDS - For validating completion requirements
    plan_approved_at: int | None = Field(
        default=None,
        description="Timestamp when plan was approved by judge_coding_plan (None=not approved)",
    )
    plan_rejection_count: int = Field(
        default=0,
        description="Number of times the plan has been rejected (max 1 allowed)",
    )
    code_approved_files: dict[str, int] = Field(
        default_factory=dict,
        description="Dictionary mapping file paths to approval timestamps from judge_code_change",
    )
    testing_approved_at: int | None = Field(
        default=None,
        description="Timestamp when testing was approved by judge_testing_implementation (None=not approved)",
    )
    all_approvals_validated: bool = Field(
        default=False,
        description="Whether all required approvals (plan, code, testing) have been validated",
    )

    def update_requirements(
        self, new_requirements: str, source: str = "update"
    ) -> None:
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
                    timestamp=self.updated_at,
                )
                self.user_requirements_history.append(version)

            # Update current requirements
            self.user_requirements = new_requirements
            self.updated_at = int(time.time())

            # Add new version to history
            new_version = RequirementsVersion(
                content=new_requirements, source=source, timestamp=self.updated_at
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
            self.updated_at = int(time.time())

    def add_test_file(self, test_file_path: str) -> None:
        """
        Add a test file to the list of test files created during testing.

        Args:
            test_file_path: Path to the test file that was created
        """
        if test_file_path not in self.test_files:
            self.test_files.append(test_file_path)
            self.updated_at = int(time.time())

    def update_test_status(self, test_type: str, status: str) -> None:
        """
        Update the status of a specific test type.

        Args:
            test_type: Type of test (unit, integration, e2e, etc.)
            status: Status (passing, failing, not_implemented, etc.)
        """
        self.test_status[test_type] = status
        self.updated_at = int(time.time())

    def get_test_coverage_summary(self) -> dict[str, Any]:
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
            "all_tests_passing": all(
                status == "passing" for status in self.test_status.values()
            )
            if self.test_status
            else False,
        }

    def update_state(self, new_state: TaskState) -> None:
        """
        Update task state and timestamp.

        Args:
            new_state: New TaskState value
        """
        if self.state != new_state:
            self.state = new_state
            self.updated_at = int(time.time())

    def add_accumulated_change(
        self, file_path: str, change_data: dict[str, Any]
    ) -> None:
        """
        Add a code change to the accumulated diff.

        Args:
            file_path: Path to the file that was changed
            change_data: Dictionary containing change information
        """
        if file_path not in self.accumulated_diff:
            self.accumulated_diff[file_path] = []

        change_entry = {**change_data, "timestamp": int(time.time())}
        self.accumulated_diff[file_path].append(change_entry)
        self.updated_at = int(time.time())

    # (Decision helpers intentionally omitted to keep HITL logic LLM-driven)

    def get_current_state_info(self) -> dict[str, str]:
        """
        Get human-readable information about current state.

        Returns:
            Dictionary with state info and next expected actions
        """
        state_info = {
            TaskState.CREATED: {
                "description": "Task created, ready for planning",
                "next_action": "Create detailed implementation plan with code analysis",
            },
            TaskState.PLANNING: {
                "description": "Planning phase in progress",
                "next_action": "Complete and validate implementation plan",
            },
            TaskState.PLAN_APPROVED: {
                "description": "Plan approved, ready for implementation",
                "next_action": "Start implementing code changes",
            },
            TaskState.IMPLEMENTING: {
                "description": "Implementation in progress",
                "next_action": "Continue implementing or transition to testing",
            },
            TaskState.TESTING: {
                "description": "Testing phase in progress",
                "next_action": "Write and run tests, ensure all tests pass",
            },
            TaskState.REVIEW_READY: {
                "description": "All tests passing, ready for final review",
                "next_action": "Validate task completion",
            },
            TaskState.COMPLETED: {
                "description": "Task completed successfully",
                "next_action": "Task is complete",
            },
            TaskState.BLOCKED: {
                "description": "Task blocked by external dependencies",
                "next_action": "Resolve blocking issues",
            },
            TaskState.CANCELLED: {
                "description": "Task cancelled",
                "next_action": "Task is cancelled",
            },
        }

        return state_info.get(
            self.state,
            {
                "description": f"Unknown state: {self.state}",
                "next_action": "Review task state",
            },
        )

    # APPROVAL TRACKING METHODS
    def mark_plan_approved(self) -> None:
        """Mark the plan as approved by judge_coding_plan."""
        self.plan_approved_at = int(time.time())
        self.updated_at = int(time.time())
        self._update_approval_validation()

    def mark_code_approved(self, file_path: str) -> None:
        """Mark a specific file's code as approved by judge_code_change."""
        self.code_approved_files[file_path] = int(time.time())
        self.updated_at = int(time.time())
        self._update_approval_validation()

    def mark_testing_approved(self) -> None:
        """Mark the testing as approved by judge_testing_implementation."""
        self.testing_approved_at = int(time.time())
        self.updated_at = int(time.time())
        self._update_approval_validation()

    def increment_plan_rejection(self) -> None:
        """Increment the plan rejection count up to the configured limit."""
        if self.plan_rejection_count < self.PLAN_REJECTION_LIMIT:
            self.plan_rejection_count += 1
        self.updated_at = int(time.time())

    def has_exceeded_plan_rejection_limit(self) -> bool:
        """Check if plan has been rejected too many times (max 1)."""
        return self.plan_rejection_count >= self.PLAN_REJECTION_LIMIT

    def get_approval_status(self) -> dict[str, Any]:
        """
        Get comprehensive approval status for task completion validation.

        Returns:
            Dictionary with approval status details
        """
        return {
            "plan_approved": self.plan_approved_at is not None,
            "plan_approved_at": self.plan_approved_at,
            "code_files_approved": len(self.code_approved_files),
            "code_approved_files": dict(self.code_approved_files),
            "all_modified_files_approved": all(
                file_path in self.code_approved_files
                for file_path in self.modified_files
            )
            if self.modified_files
            else True,
            "testing_approved": self.testing_approved_at is not None,
            "testing_approved_at": self.testing_approved_at,
            "all_approvals_validated": self.all_approvals_validated,
            "missing_approvals": self._get_missing_approvals(),
        }

    def _get_missing_approvals(self) -> list[str]:
        """Get list of missing approvals."""
        missing = []

        if self.plan_approved_at is None:
            missing.append("plan approval (judge_coding_plan)")

        if self.modified_files:
            unapproved_files = [
                f for f in self.modified_files if f not in self.code_approved_files
            ]
            if unapproved_files:
                missing.append(
                    f"code approval for files: {', '.join(unapproved_files)}"
                )

        if self.test_files and self.testing_approved_at is None:
            missing.append("testing approval (judge_testing_implementation)")

        return missing

    def _update_approval_validation(self) -> None:
        """Update the all_approvals_validated flag based on current approvals."""
        missing_approvals = self._get_missing_approvals()
        self.all_approvals_validated = len(missing_approvals) == 0

    def validate_completion_readiness(self) -> dict[str, Any]:
        """
        Validate if task is ready for completion based on approvals.

        Returns:
            Dictionary with validation results
        """
        approval_status = self.get_approval_status()
        missing_approvals = approval_status["missing_approvals"]

        is_ready = (
            approval_status["plan_approved"]
            and approval_status["all_modified_files_approved"]
            and (approval_status["testing_approved"] or len(self.test_files) == 0)
        )

        return {
            "ready_for_completion": is_ready,
            "approval_status": approval_status,
            "missing_approvals": missing_approvals,
            "validation_message": (
                "✅ All required approvals completed"
                if is_ready
                else f"❌ Missing approvals: {', '.join(missing_approvals)}"
            ),
        }

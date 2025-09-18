"""
Core task state definitions for MCP as a Judge.

This module contains the TaskState enum that is used throughout the system
to track the state of coding tasks. It's placed in core to avoid circular imports.
"""

from enum import Enum


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

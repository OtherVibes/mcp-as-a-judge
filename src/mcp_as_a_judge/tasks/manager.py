"""
Coding task manager for enhanced MCP as a Judge workflow v3.

This module provides helper functions for managing coding tasks,
including creation, updates, state transitions, and persistence.
"""

import json
import time

from pydantic import ValidationError

from mcp_as_a_judge.core.logging_config import get_logger
from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskSize, TaskState

# Set up logger using custom get_logger function
logger = get_logger(__name__)


async def create_new_coding_task(
    user_request: str,
    task_title: str,
    task_description: str,
    user_requirements: str,
    tags: list[str],
    conversation_service: ConversationHistoryService,
    task_size: TaskSize,
) -> TaskMetadata:
    """
    Create a new coding task with auto-generated task_id.

    Args:
        user_request: Original user request
        task_title: Display title
        task_description: Detailed description
        user_requirements: Initial requirements
        tags: Task tags
        conversation_service: Conversation service
        task_size: Task size classification (REQUIRED)

    Returns:
        New TaskMetadata instance
    """

    logger.info(f"Creating new coding task: {task_title}")

    # Create new TaskMetadata with auto-generated UUID
    task_metadata = TaskMetadata(
        title=task_title,
        description=task_description,
        user_requirements=user_requirements,
        state=TaskState.CREATED,  # Default state for new tasks
        task_size=task_size,
        tags=tags,
    )

    # Add initial requirements to history if provided
    if user_requirements:
        task_metadata.update_requirements(user_requirements, source="initial")

    logger.info(f"Created new task metadata: {task_metadata.task_id}")
    return task_metadata


async def update_existing_coding_task(
    task_id: str,
    user_request: str,
    task_title: str,
    task_description: str,
    user_requirements: str | None,
    state: TaskState | None,
    tags: list[str],
    conversation_service: ConversationHistoryService,
) -> TaskMetadata:
    """
    Update an existing coding task.

    Args:
        task_id: Immutable task ID
        user_request: Original user request
        task_title: Updated title
        task_description: Updated description
        user_requirements: Updated requirements
        state: Updated state (None to skip state update)
        tags: Updated tags
        conversation_service: Conversation service

    Returns:
        Updated TaskMetadata instance

    Raises:
        ValueError: If task not found or invalid state transition
    """
    logger.info(f"Updating existing coding task: {task_id}")

    # Load existing task metadata from conversation history
    existing_metadata = await load_task_metadata_from_history(
        task_id=task_id,
        conversation_service=conversation_service,
    )

    if not existing_metadata:
        raise ValueError(f"Task not found: {task_id}")

    # Update mutable fields
    existing_metadata.title = task_title
    existing_metadata.description = task_description
    existing_metadata.tags = tags
    existing_metadata.updated_at = int(time.time())

    # Update requirements if provided
    if user_requirements is not None:
        existing_metadata.update_requirements(user_requirements, source="update")

    # Update state if provided (with validation)
    if state is not None:
        validate_state_transition(existing_metadata.state, state)
        existing_metadata.update_state(state)

    logger.info(f"Updated task metadata: {task_id}")
    return existing_metadata


async def load_task_metadata_from_history(
    task_id: str,
    conversation_service: ConversationHistoryService,
) -> TaskMetadata | None:
    """
    Load TaskMetadata from conversation history using task_id as primary key.

    Args:
        task_id: Task ID to load
        conversation_service: Conversation service

    Returns:
        TaskMetadata if found, None otherwise
    """
    try:
        # Use task_id as primary key for conversation history
        conversation_history = (
            await conversation_service.load_filtered_context_for_enrichment(
                session_id=task_id
            )
        )

        # Strategy: prefer the most recent record that explicitly includes a state.
        # Some tool outputs serialize with exclude_defaults=True, which can omit
        # default-valued fields like state when it's 'created'. That can cause
        # state to be implicitly reset to CREATED when reloading. To guard
        # against that, we (1) look for the newest record with an explicit state;
        # if not found, (2) take the newest metadata snapshot and backfill the
        # state from the most recent earlier snapshot that has it.

        latest_snapshot: dict | None = None

        # IMPORTANT: conversation_history is returned in reverse chronological order
        # (newest first). Iterate in that order so we always prefer the latest state.
        # Pass 1: newest → oldest, return first snapshot with explicit state
        for record in conversation_history:
            try:
                output_data = json.loads(record.output)
            except json.JSONDecodeError:
                continue

            if not isinstance(output_data, dict):
                continue

            if "current_task_metadata" not in output_data:
                continue

            metadata_dict = output_data["current_task_metadata"]
            if not isinstance(metadata_dict, dict):
                continue

            # Keep the newest snapshot as a fallback for pass 2 (first iteration)
            if latest_snapshot is None:
                latest_snapshot = dict(metadata_dict)

            # Prefer snapshots that explicitly carry state
            if metadata_dict.get("state"):
                try:
                    return TaskMetadata.model_validate(metadata_dict)
                except ValidationError:
                    # If this specific snapshot fails validation, keep searching
                    continue

        # Pass 2: if newest snapshot lacks state, try to backfill from older records
        if latest_snapshot is not None and "state" not in latest_snapshot:
            for record in conversation_history:
                try:
                    output_data = json.loads(record.output)
                except json.JSONDecodeError:
                    continue

                if not isinstance(output_data, dict):
                    continue

                if "current_task_metadata" not in output_data:
                    continue

                older_md = output_data["current_task_metadata"]
                if (
                    isinstance(older_md, dict)
                    and "state" in older_md
                    and older_md["state"]
                ):
                    # Backfill only the missing state to avoid unintended resets
                    latest_snapshot["state"] = older_md["state"]
                    break

            # As a final safeguard, infer a reasonable state from approval markers
            # if no explicit state could be found in history.
            if "state" not in latest_snapshot:
                try:
                    # If testing was approved, task must be at least TESTING
                    if latest_snapshot.get("testing_approved_at"):
                        latest_snapshot["state"] = TaskState.TESTING.value
                    # If any code files were approved, the task transitioned to TESTING after review
                    elif latest_snapshot.get("code_approved_files"):
                        code_approved_files = latest_snapshot.get("code_approved_files")
                        if (
                            isinstance(code_approved_files, dict)
                            and len(code_approved_files) > 0
                        ):
                            latest_snapshot["state"] = TaskState.TESTING.value
                    # If plan was approved, set PLAN_APPROVED
                    elif latest_snapshot.get("plan_approved_at"):
                        latest_snapshot["state"] = TaskState.PLAN_APPROVED.value
                except Exception:  # nosec B110
                    # Best-effort inference only
                    pass

            try:
                return TaskMetadata.model_validate(latest_snapshot)
            except ValidationError:
                # Fall through to None if even the merged snapshot is invalid
                pass

        return None

    except Exception as e:
        logger.warning(f"Failed to load task metadata from history: {e}")
        return None


async def save_task_metadata_to_history(
    task_metadata: TaskMetadata,
    user_request: str,
    action: str,
    conversation_service: ConversationHistoryService,
) -> None:
    """
    Save TaskMetadata to conversation history using task_id as primary key.

    Args:
        task_metadata: Task metadata to save
        user_request: Original user request
        action: Action taken ("created" or "updated")
        conversation_service: Conversation service
    """
    try:
        # Use task_id as primary key for conversation history
        await conversation_service.save_tool_interaction_and_cleanup(
            session_id=task_metadata.task_id,
            tool_name="set_coding_task",
            tool_input=user_request,
            tool_output=json.dumps(
                {
                    "action": action,
                    "current_task_metadata": task_metadata.model_dump(mode="json"),
                    "timestamp": int(time.time()),
                }
            ),
        )

        logger.info(
            f"Saved task metadata to conversation history: {task_metadata.task_id}"
        )

    except Exception as e:
        logger.error(f"Failed to save task metadata to history: {e}")
        # Don't raise - this is not critical for tool operation


def validate_state_transition(current_state: TaskState, new_state: TaskState) -> None:
    """
    Validate that the state transition is allowed.

    Args:
        current_state: Current TaskState
        new_state: Requested new TaskState

    Raises:
        ValueError: If transition is not allowed
    """
    # Define valid state transitions
    valid_transitions = {
        TaskState.CREATED: [TaskState.PLANNING, TaskState.BLOCKED, TaskState.CANCELLED],
        TaskState.PLANNING: [
            TaskState.PLAN_APPROVED,
            TaskState.CREATED,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
        ],
        TaskState.PLAN_APPROVED: [
            TaskState.IMPLEMENTING,
            TaskState.PLANNING,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
        ],
        TaskState.IMPLEMENTING: [
            TaskState.IMPLEMENTING,
            TaskState.REVIEW_READY,
            TaskState.PLAN_APPROVED,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
        ],
        TaskState.REVIEW_READY: [
            TaskState.COMPLETED,
            TaskState.IMPLEMENTING,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
        ],
        TaskState.COMPLETED: [
            TaskState.CANCELLED
        ],  # Only allow cancellation of completed tasks
        TaskState.BLOCKED: [
            TaskState.CREATED,
            TaskState.PLANNING,
            TaskState.PLAN_APPROVED,
            TaskState.IMPLEMENTING,
            TaskState.REVIEW_READY,
            TaskState.CANCELLED,
        ],
        TaskState.CANCELLED: [],  # No transitions from cancelled state
    }

    if new_state not in valid_transitions.get(current_state, []):
        raise ValueError(
            f"Invalid state transition: {current_state.value} → {new_state.value}. "
            f"Valid transitions from {current_state.value}: {[s.value for s in valid_transitions.get(current_state, [])]}"
        )

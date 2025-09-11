"""
Coding task manager for enhanced MCP as a Judge workflow v3.

This module provides helper functions for managing coding tasks,
including creation, updates, state transitions, and persistence.
"""

import json
import time

from pydantic import ValidationError

from mcp_as_a_judge.db.conversation_history_service import ConversationHistoryService
from mcp_as_a_judge.logging_config import get_logger
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

    logger.info(f"📝 Creating new coding task: {task_title}")

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

    logger.info(f"✅ Created new task metadata: {task_metadata.task_id}")
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
    logger.info(f"📝 Updating existing coding task: {task_id}")

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

    logger.info(f"✅ Updated task metadata: {task_id}")
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
        conversation_history = await conversation_service.get_conversation_history(
            session_id=task_id
        )

        # Look for the most recent task metadata record from any source
        # (not just set_coding_task, since other tools also save task metadata)
        for record in reversed(conversation_history):
            try:
                # Parse the record output to look for task metadata
                output_data = json.loads(record.output)
                if "current_task_metadata" in output_data:
                    metadata_dict = output_data["current_task_metadata"]
                    return TaskMetadata.model_validate(metadata_dict)
            except (json.JSONDecodeError, ValidationError):
                # Skip records that can't be parsed or validated
                continue

        return None

    except Exception as e:
        logger.warning(f"⚠️ Failed to load task metadata from history: {e}")
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
        await conversation_service.save_tool_interaction(
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
            f"💾 Saved task metadata to conversation history: {task_metadata.task_id}"
        )

    except Exception as e:
        logger.error(f"❌ Failed to save task metadata to history: {e}")
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

# Get Current Coding Task

## Description
Retrieve the most recently active coding task UUID (task_id) and metadata from conversation history. Use when the task_id is missing from context.

{% include 'shared/critical_tool_warnings.md' %}

## When to use
- Need the task_id for follow-up tool calls
- Want to resume the last active coding task

## Args
- None

## Returns
- `found`: boolean — whether a recent task was found
- `task_id`: string — task UUID (present when found)
- `last_activity`: integer — last-activity timestamp for the session
- `current_task_metadata`: object — TaskMetadata (when available)
- `workflow_guidance`: object — WorkflowGuidance with `next_tool`, preparation, and guidance

## Notes
- After recovery, always use the exact `task_id` UUID in all subsequent tool calls. Do not invent or transform the value.

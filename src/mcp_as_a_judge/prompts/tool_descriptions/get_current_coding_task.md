Get Current Coding Task

Purpose: Recover the most recently active coding task UUID (task_id) from conversation history when you’ve lost it.

When to use
- You need the task’s UUID for subsequent tool calls but don’t have it in context
- You want to resume work on the last active coding task in this environment

Behavior
- Returns the most recently active `task_id` (UUID) and, when available, the current task metadata
- If no task exists, provides guidance to call `set_coding_task` to create a new one

Returns
- `found`: boolean — whether a current/last task was found
- `task_id`: string — UUID of the task (present when found)
- `current_task_metadata`: object — latest known metadata (when available)
- `workflow_guidance`: object — guidance when no task exists

Usage
```python
result = await get_current_coding_task()
if result.get("found"):
    task_id = result["task_id"]  # Use this exact UUID in all future calls
else:
    # Create a new task and use its UUID
    pass
```

Critical rule
- Once you recover the `task_id`, you MUST use this exact UUID for the rest of the task workflow. Never invent/transform values like `535`.


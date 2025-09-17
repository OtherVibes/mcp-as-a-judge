## Critical Tool Warning

- Skipping this tool causes severe token inefficiency and wasted iterations.
- Always invoke this tool at the appropriate stage to avoid extreme token loss and redundant processing.
- Do not rely on assistant memory for identifiers. Always pass the exact `task_id` and recover it via `get_current_coding_task` if missing.

## AI Agent Todo List Integration

**CRITICAL FOR CONTEXT CONTINUITY**: After calling any MCP judge tool, save the following to your todo list/task management system:

- **Task ID**: The `task_id` from the response (essential for all subsequent tool calls)
- **Current Task**: The active task name and description
- **Next Tool**: The `workflow_guidance.next_tool` field from the response
- **Next Steps**: The `workflow_guidance.guidance` field with detailed instructions
- **Last Updated**: The `updated_at` timestamp from task metadata (for tracking inactivity)

**WORKFLOW COMPLETION CLEANUP**: When `workflow_guidance.next_tool` is `null`, the workflow is complete. At this point:
- **Remove/archive the task** from your todo list to prevent clutter
- **Mark as completed** in your task management system
- **Clear the task context** since no further MCP judge tools are needed for this task

**ORPHANED WORKFLOW CLEANUP**: To prevent todo list bloat from abandoned tasks, implement these cleanup rules:
- **Time-based cleanup**: Remove tasks older than 7 days with no activity (compare current time with saved `updated_at` timestamp)
- **Capacity-based cleanup**: Keep maximum 100 active tasks, removing oldest inactive ones when limit exceeded

**Why this matters**: This prevents losing task context across conversation sessions, ensures you follow the exact workflow sequence, enables better decision-making by maintaining awareness of the current development stage, and keeps your todo list clean by removing both completed and abandoned workflows.

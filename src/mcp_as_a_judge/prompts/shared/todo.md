## AI Coding Assistant Todo List Integration Guidelines

**CRITICAL FOR CONTEXT CONTINUITY**: After calling any MCP judge tool, save the following to your todo list/task management system:

- **Task ID**: The `task_id` from the response (essential for all subsequent tool calls)
- **Current Task**: The active task name and description
- **Next Tool**: The `workflow_guidance.next_tool` field from the response
- **Next Steps**: The `workflow_guidance.guidance` field with detailed instructions
- **Last Updated**: The `updated_at` timestamp from task metadata (for tracking inactivity)

**Why this matters**: This prevents losing task context across conversation sessions, ensures you follow the exact workflow sequence, enables better decision-making by maintaining awareness of the current development stage, and keeps your todo list clean by removing both completed and abandoned workflows.

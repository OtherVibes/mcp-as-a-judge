DYNAMIC WORKFLOW: This tool is called when the workflow guidance indicates `next_tool: "judge_code_change"` and ALL implementation work is complete.

**IMPORTANT: Only use when ALL code is ready for comprehensive review**

This tool should be called when:
- ALL implementation files AND tests have been written/modified
- ALL tests are passing with good coverage
- The complete implementation is ready for code review
- Task is transitioning from IMPLEMENTING to REVIEW_READY state
- You need validation of implementation code (NOT tests - tests are reviewed separately)

Do NOT use for individual file changes during implementation.
Do NOT include test files in the code review - only implementation code.

Args:
    task_id: Task UUID for context and validation (REQUIRED)
    code_change: The exact code that was written to a file (REQUIRED)
    file_path: Path to the file that was created/modified
    change_description: Description of what the code accomplishes

Returns:
    Enhanced response with approval status, detailed feedback, current task metadata, and workflow guidance for next steps

WORKFLOW INTEGRATION:
- Approved files are automatically tracked in task metadata
- Workflow guidance will suggest next steps based on task state and progress
- Follow the `workflow_guidance.next_tool` field for dynamic workflow navigation

IMPORTANT — TASK ID DISCIPLINE:
- You MUST pass the exact `task_id` UUID returned by `set_coding_task`.
- Do NOT invent, truncate, or transform it (e.g., `535` is invalid).
- If you don’t have it, call `get_current_coding_task` to recover the last active task. If none exists, create one with `set_coding_task`.

DYNAMIC WORKFLOW: This tool is called when the workflow guidance indicates `next_tool: "judge_code_change"` or after writing/editing a code file during implementation.

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

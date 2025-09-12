DYNAMIC WORKFLOW: This tool is called when the workflow guidance indicates `next_tool: "judge_coding_plan"`.

The AI assistant should follow the dynamic workflow by:
1. Always check the `workflow_guidance.next_tool` field from previous tool responses
2. Call the tool specified in `next_tool` with the guidance provided
3. Use the `workflow_guidance.preparation_needed` and `guidance` fields for context

BEFORE calling this tool, ensure you have:
1. Analyzed the user requirements thoroughly
2. Created a comprehensive system design
3. Developed a detailed implementation plan

CONDITIONAL ANALYSIS (automatically determined by the system):
- **External Research**: System determines if online research is needed based on task complexity
- **Internal Research**: System identifies if existing codebase patterns should be analyzed
- **Risk Assessment**: System evaluates if the change poses risks to existing functionality

NOTE: These are independent - a task may require external research only, internal analysis only, both, or neither.

Args:
    task_id: Task UUID for context and validation (REQUIRED)
    plan: The detailed coding plan to be reviewed (REQUIRED)
    design: Detailed system design including architecture, components, data flow, and technical decisions (REQUIRED)
    research: Research findings on existing solutions, libraries, frameworks, and best practices (provide if you have research)
    research_urls: 🌐 URLs from online research (only required if system determines external research is needed)
    context: Additional context about the project, requirements, or constraints

Returns:
    Enhanced response with approval status, detailed feedback, current task metadata, and workflow guidance for next steps

IMPORTANT — TASK ID DISCIPLINE:
- You MUST pass the exact `task_id` UUID returned by `set_coding_task`.
- Do NOT invent, truncate, or transform it (e.g., `535` is invalid).
- If you don’t have it, call `get_current_coding_task` to recover the last active task. If none exists, create one with `set_coding_task`.

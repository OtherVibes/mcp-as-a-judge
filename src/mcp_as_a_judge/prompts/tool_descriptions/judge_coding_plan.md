DYNAMIC WORKFLOW: This tool is called when the workflow guidance indicates `next_tool: "judge_coding_plan"`.

The AI assistant should follow the dynamic workflow by:
1. Always check the `workflow_guidance.next_tool` field from previous tool responses
2. Call the tool specified in `next_tool` with the guidance provided
3. Use the `workflow_guidance.preparation_needed` and `guidance` fields for context

BEFORE calling this tool, ensure you have:
1. Analyzed the user requirements thoroughly
2. Performed ONLINE research on existing solutions and well-known libraries
3. Analyzed the repository code for existing patterns and components
4. Created a comprehensive system design
5. Developed a detailed implementation plan

Args:
    task_id: Task UUID for context and validation (REQUIRED)
    plan: The detailed coding plan to be reviewed (REQUIRED)
    design: Detailed system design including architecture, components, data flow, and technical decisions (REQUIRED)
    research: Research findings on existing solutions, libraries, frameworks, and best practices (REQUIRED)
    research_urls: 🌐 URLs from MANDATORY online research - AI assistant MUST provide at least 3 URLs from research (REQUIRED)
    context: Additional context about the project, requirements, or constraints

Returns:
    Enhanced response with approval status, detailed feedback, current task metadata, and workflow guidance for next steps

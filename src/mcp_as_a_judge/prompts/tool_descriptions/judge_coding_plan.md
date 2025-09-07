MANDATORY: AI programming assistant MUST call this tool whenever you start to work on a coding task.

BEFORE calling this tool, AI programming assistant MUST collaborate with the user to:
1. Analyze the user requirements
2. Peform an ONLINE research on what is the best way to implement user requirements, focusing on existing well-known libraries
3. Analyze the repository code to check what is the best way to implement the solution with minimum changes
4. Create a system design that matches the user requirements
5. Create implementation plan

Args:
    plan: The detailed coding plan to be reviewed (REQUIRED)
    design: Detailed system design including architecture, components, data flow, and technical decisions (REQUIRED)
    research: Research findings on existing solutions, libraries, frameworks, and best practices (REQUIRED)
    research_urls: 🌐 URLs from MANDATORY online research - AI assistant MUST provide at least 3 URLs from research (REQUIRED)
    user_requirements: Clear statement of what the user wants to achieve (REQUIRED)
    context: Additional context about the project, requirements, or constraints

Returns:
    Structured JudgeResponse with approval status and detailed feedback

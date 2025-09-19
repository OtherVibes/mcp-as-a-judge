## AI Agent Todo List Integration Guidelines

**CRITICAL FOR CONTEXT CONTINUITY**: After calling any MCP judge tool, save the following to your todo list/task management system:

- **Task ID**: The `task_id` from the response (essential for all subsequent tool calls)
- **Current Task**: The active task name and description
- **Current State**: The task state (e.g., CREATED, REQUIREMENTS_FEEDBACK, USER_APPROVE_REQUIREMENTS, PLANNING, etc.)
- **Next Tool**: The `workflow_guidance.next_tool` field from the response
- **Next Steps**: The `workflow_guidance.guidance` field with detailed instructions
- **Technical Decisions**: Any technology stack decisions made during requirement gathering
- **User Feedback**: Key user feedback and requirement clarifications from brainstorming phase
- **Last Updated**: The `updated_at` timestamp from task metadata (for tracking inactivity)

**Why this matters**: This prevents losing task context across conversation sessions, ensures you follow the exact workflow sequence, enables better decision-making by maintaining awareness of the current development stage, and keeps your todo list clean by removing both completed and abandoned workflows.

## Mandatory Workflow Steps (NEVER SKIP)

**PHASE 1: BRAINSTORMING** (Mandatory for all tasks, saved to database):
1. **get_user_feedback**: Gather detailed requirements and clarifications from user
2. **AI Assistant**: Create comprehensive implementation plan based on user feedback
3. **get_user_approve_requirement**: Present plan to user for approval

**PHASE 2: TECHNICAL VALIDATION** (LLM validation, saved to database):
4. **judge_coding_plan**: LLM validates technical aspects of user-approved plan

**PHASE 3: IMPLEMENTATION** (Formal workflow, saved to database):
5. **judge_code_change**: Validate complete code implementations
6. **judge_testing_implementation**: Validate testing implementation and coverage
7. **judge_coding_task_completion**: Final validation of task completion

**CRITICAL ITERATION LOGIC**:
- **If user doesn't approve plan**: Go back to get_user_feedback (refine requirements)
- **If user approves but LLM rejects**: Go back to plan creation (technical issues)
- **If LLM approves**: Proceed to implementation

**Key Tracking Points**:
- Track technology stack decisions made during requirement gathering
- Maintain user feedback and requirement clarifications throughout task lifetime
- Ensure approved plans use agreed-upon technologies and best practices
- Monitor state transitions: CREATED → REQUIREMENTS_FEEDBACK → USER_APPROVE_REQUIREMENTS → PLANNING → PLAN_APPROVED

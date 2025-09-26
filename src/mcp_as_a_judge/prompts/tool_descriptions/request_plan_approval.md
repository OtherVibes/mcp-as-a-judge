# Request Plan Approval

## Description
Present a completed plan to the user for approval before proceeding to AI judge validation. This tool enables human-in-the-loop plan review and iterative refinement based on user feedback.

## When to use
- After creating a detailed implementation plan but before calling judge_coding_plan
- When the task is in PLANNING state and a complete plan has been prepared
- To enable user review and approval of plans before AI validation

## Prerequisites
- Task must be in PLANNING state
- Complete plan, design, and research must be prepared
- Task metadata must exist (call set_coding_task first if needed)

## Args
- `plan`: string — Detailed implementation plan with step-by-step approach (required)
- `design`: string — Technical design and architecture decisions (required)
- `research`: string — Research summary and findings (required)
- `task_id`: string — Task UUID (required)
- `research_urls`: list[string] — URLs from external research sources (optional)
- `problem_domain`: string — Problem domain statement (optional)
- `problem_non_goals`: list[string] — Non-goals and scope boundaries (optional)
- `library_plan`: list[dict] — Library selection map with purpose, selection, source (optional)
- `internal_reuse_components`: list[dict] — Internal components to reuse with paths (optional)

## Returns
- `approved`: boolean — Whether the user approved the plan
- `user_feedback`: string — User's feedback or modification requests
- `next_action`: string — Recommended next step based on user decision

## User Options
The tool presents three options to the user:
1. **Approve** — Proceed with the plan as-is (transitions to PLAN_APPROVED state)
2. **Modify** — Request changes to the plan (returns to PLANNING state with feedback)
3. **Reject** — Start over with a different approach (returns to PLANNING state)

## Workflow Integration
- **On Approval**: Task remains in PLAN_PENDING_APPROVAL state, ready for judge_coding_plan AI validation
- **On Modification**: Task returns to PLANNING state with user feedback integrated
- **On Rejection**: Task returns to PLANNING state for complete plan revision

## Notes
- This tool uses the MCP elicitation system to present plans in a user-friendly format
- User feedback is automatically integrated into task requirements for plan iteration
- The tool maintains full audit trails of user decisions and feedback
- Always use the exact `task_id`; recover it via `get_current_coding_task` if missing

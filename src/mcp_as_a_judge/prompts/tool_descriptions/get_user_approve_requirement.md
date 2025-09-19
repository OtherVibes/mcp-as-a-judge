# Get User Approve Requirement

## Description
**MANDATORY APPROVAL STEP**: Present a formatted implementation plan to the user for review and approval. This step is REQUIRED for ALL tasks regardless of size before any development begins.

## Args
- `plan`: string — Raw implementation plan content to be formatted
- `design`: string — Design details and architecture information
- `research`: string — Research findings and analysis
- `technical_decisions`: list[dict] — Key technical decisions made (format: {"decision": "framework", "choice": "FastAPI", "rationale": "..."})
- `implementation_scope`: dict — Scope breakdown with estimated effort (format: {"files_to_create": [...], "files_to_modify": [...], "estimated_complexity": "medium"})
- `language_specific_practices`: list[string] — Best practices that will be followed for the chosen technology stack
- `task_id`: string — Task ID for context tracking
- `user_questions`: list[string] (optional) — Specific questions for user feedback (auto-generated if not provided)

## Returns
- `PlanApprovalResult`: Structured result containing user approval status, feedback, and any requirement updates

## Usage Context
- **MANDATORY FOR ALL TASKS** regardless of size (XS, S, M, L, XL)
- **REQUIRED APPROVAL STEP** - never skip user plan approval
- Called after initial plan creation to get user approval
- Automatically formats the plan using PlanFormatter for IDE-friendly display
- Generates relevant user questions if not provided
- For XS/S tasks: transitions directly to PLAN_APPROVED (skips LLM validation)
- For M/L/XL tasks: transitions to PLANNING state for technical validation
- Presents plan in markdown format optimized for IDEs like Cursor and Copilot
- Captures user feedback for plan refinement if needed
- Integrates approved plan into task requirements
- Part of the brainstorming phase - interactions are saved to database for LLM context
- **CRITICAL ITERATION**: If user rejects plan, returns to REQUIREMENTS_FEEDBACK state for more brainstorming

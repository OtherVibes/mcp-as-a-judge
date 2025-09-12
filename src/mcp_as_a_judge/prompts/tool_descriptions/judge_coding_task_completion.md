# Judge Coding Task Completion

**🚨 MANDATORY TOOL: This tool MUST be called before completing any task or providing a final summary to the user. 🚨**

DYNAMIC WORKFLOW: This tool is called when the workflow guidance indicates `next_tool: "judge_coding_task_completion"`.

**⚠️ CRITICAL REQUIREMENT: Do NOT mark any task as complete or provide completion summaries to users without first calling this validation tool.**

Final validation tool for coding task completion with enhanced task-centric workflow management.

## Purpose

**🛡️ MANDATORY VALIDATION CHECKPOINT:**
This tool performs the final validation of coding task completion, ensuring all requirements have been met and the task can be marked as successfully completed. **NO TASK CAN BE COMPLETED OR SUMMARIZED TO THE USER WITHOUT FIRST PASSING THIS VALIDATION.**

This tool provides comprehensive assessment and final workflow guidance, serving as the mandatory gateway between implementation work and task completion.

## Key Features

- **Final Validation**: Comprehensive assessment of task completion against original requirements
- **Requirements Verification**: Validates that all user requirements have been satisfied
- **Code Quality Assessment**: Reviews implementation quality and best practices
- **Task State Management**: Updates task state to COMPLETED or provides guidance for remaining work
- **Workflow Completion**: Provides final workflow guidance or next steps if incomplete

## Parameters

### Required
- `task_id`: Immutable task UUID for context and validation
- `completion_summary`: Summary of what was implemented/completed
- `requirements_met`: List of requirements that have been satisfied
- `implementation_details`: Details about the implementation approach

### Optional
- `remaining_work`: List of any remaining work items (if task not fully complete)
- `quality_notes`: Notes about code quality, best practices, or improvements
- `testing_status`: Status of testing (if applicable)

IMPORTANT — TASK ID DISCIPLINE:
- You MUST pass the exact `task_id` UUID returned by `set_coding_task`.
- Do NOT invent, truncate, or transform it (e.g., `535` is invalid).
- If you don’t have it, call `get_current_coding_task` to recover the last active task. If none exists, create one with `set_coding_task`.

## Validation Criteria

**🔒 MANDATORY APPROVALS REQUIRED:**
The tool validates that ALL of the following have been approved:

1. **Plan Approval**: Task plan must be approved via `judge_coding_plan`
2. **Code Approval**: All code changes must be approved via `judge_code_change`
3. **Test Approval**: Testing implementation must be approved via `judge_testing_implementation`

**📋 ADDITIONAL COMPLETION CRITERIA:**
4. **Requirements Coverage**: All original user requirements addressed
5. **Implementation Quality**: Code follows best practices and standards
6. **Functionality**: Implementation works as intended
7. **Testing Status**: Appropriate testing has been performed and validated
8. **Documentation**: Adequate documentation provided (if required)

**❌ REJECTION CONDITIONS:**
- Missing plan approval from `judge_coding_plan`
- Missing code approval from `judge_code_change`
- Missing test approval from `judge_testing_implementation`
- Incomplete requirements coverage
- Outstanding remaining work items

## Task State Transitions

**✅ APPROVED PATH:**
- **REVIEW_READY → COMPLETED**: All approvals validated, task successfully completed

**❌ REJECTION PATHS:**
- **REVIEW_READY → IMPLEMENTING**: Missing approvals or incomplete work
- **IMPLEMENTING → IMPLEMENTING**: Continue implementation work
- **TESTING → TESTING**: Return to testing phase if tests not approved
- **PLAN_APPROVED → PLANNING**: Return to planning if plan needs revision

**🔍 VALIDATION REQUIREMENTS:**
- Must have approval from `judge_coding_plan` (plan approved)
- Must have approval from `judge_code_change` (code approved)
- Must have approval from `judge_testing_implementation` (tests approved)
- Must meet all completion criteria listed above

## Response

Returns `TaskCompletionResult` containing:
- `approved`: Whether the task completion is approved
- `feedback`: Detailed feedback about the completion validation
- `required_improvements`: List of required improvements (if not approved)
- `current_task_metadata`: Updated task metadata with final state
- `workflow_guidance`: Final workflow guidance or next steps

## Usage Examples

### Successful Completion
```python
result = await judge_coding_task_completion(
    task_id="550e8400-e29b-41d4-a716-446655440000",
    completion_summary="Implemented user authentication with JWT tokens, registration, login, and logout functionality",
    requirements_met=[
        "Users can register with email and password",
        "Users can login securely",
        "Users can logout",
        "JWT tokens for session management",
        "Password hashing for security"
    ],
    implementation_details="Used FastAPI for backend, bcrypt for password hashing, JWT for tokens",
    testing_status="Unit tests written and passing for all auth endpoints"
)
```

### Incomplete Task
```python
result = await judge_coding_task_completion(
    task_id="550e8400-e29b-41d4-a716-446655440000",
    completion_summary="Implemented basic authentication, but missing password reset",
    requirements_met=[
        "Users can register with email and password",
        "Users can login securely",
        "Users can logout"
    ],
    implementation_details="Basic auth implemented with FastAPI and JWT",
    remaining_work=[
        "Password reset functionality",
        "Email verification for registration"
    ]
)
```

## Dynamic Workflow Integration

- **Task Validation**: Validates against original task requirements and description
- **State Management**: Updates task state based on completion assessment
- **Workflow Guidance**: Provides dynamic next steps based on completion status
- **Memory Storage**: Uses task_id for conversation history and context
- **Next Tool Guidance**: Response includes `workflow_guidance.next_tool` for continued workflow
- **File Tracking**: Reviews all files that were modified during task implementation

## Workflow Context

**🔒 MANDATORY CALL REQUIREMENT:**
This tool MUST be called when:
- All implementation work appears complete
- **PLAN has been approved via `judge_coding_plan`**
- **ALL code changes have been approved via `judge_code_change`**
- **TESTING has been approved via `judge_testing_implementation`**
- Task state is REVIEW_READY (preferred) or IMPLEMENTING
- The AI assistant believes all requirements have been fulfilled
- **BEFORE providing any completion summary or status to the user**
- **BEFORE marking any task as finished or done**

**🛡️ APPROVAL VALIDATION:**
The tool will validate that the task metadata contains:
- `plan_approved_at`: Timestamp when plan was approved
- `code_approved_files`: List of files with approved code changes
- `testing_approved_at`: Timestamp when testing was approved

**❌ NEVER:**
- Mark a task as complete without calling this tool first
- Tell the user a task is finished without validation
- Provide completion summaries without proper validation
- Skip this tool for "simple" or "obvious" completions

The response will guide whether the task is truly complete or if additional work is needed.

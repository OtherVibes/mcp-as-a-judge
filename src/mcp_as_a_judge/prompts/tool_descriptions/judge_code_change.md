# Judge Code Change

## Description
Review implementation code (not tests) when implementation changes are ready for review. Tests are validated separately by `judge_testing_implementation`. Called when `workflow_guidance.next_tool == "judge_code_change"`.

{% include 'shared/critical_tool_warnings.md' %}

## When to use
- After creating or modifying implementation code and a review is needed. Tests may be written before or after review; they are validated via `judge_testing_implementation`.

## Human-in-the-Loop (HITL) checks
- If foundational choices are unclear or need confirmation (e.g., framework/library, UI vs CLI, web vs desktop, API style, auth, hosting), first call `raise_missing_requirements` to elicit the user’s intent
- If the implementation proposes changing a previously described/understood fundamental choice, call `raise_obstacle` to involve the user in selecting the new direction
- These HITL tools do not return `next_tool`; follow workflow guidance for the next step after elicitation

## Args
- `task_id`: string — Task UUID (required)
- `code_change`: string — Exact code content for the file (required)
- `file_path`: string — Path to the created/modified file
- `change_description`: string — What the change accomplishes

## Returns
- Response JSON schema (JudgeResponse):
```json
{{ JUDGE_RESPONSE_SCHEMA }}
```

- Review only implementation code here; tests are validated via `judge_testing_implementation`.
- Always use the exact `task_id`; recover it via `get_current_coding_task` if missing.
- If HITL was performed, update the task description/requirements via `set_coding_task` if text needs to be clarified for future steps

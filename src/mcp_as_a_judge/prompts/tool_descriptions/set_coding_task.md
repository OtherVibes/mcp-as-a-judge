# Set Coding Task

## Description
Create or update coding task metadata and receive dynamic workflow guidance. This is the mandatory entry point for any coding work.

{% include 'shared/critical_tool_warnings.md' %}

## When to use
- Any user request requiring logical code changes or creation of new files (new apps, features, refactors, bug fixes)

## Args
- `user_request`: string — Original user request (required for new tasks)
- `task_title`: string — Task title (required for new tasks)
- `task_description`: string — Detailed description (required for new tasks)
- `task_size`: enum — One of `xs|s|m|l|xl` (default `m`)
- `task_id`: string — Task UUID when updating an existing task (optional)
- `user_requirements`: string — Updated requirements (optional)
- `state`: enum — Optional state transition when updating an existing task. Valid transitions are enforced (e.g., `plan_approved` → `implementing`).
- `tags`: list[string] — Task tags (optional)

## Returns
- Response JSON schema (TaskAnalysisResult):
```json
{{ TASK_ANALYSIS_RESULT_SCHEMA }}
```

## Notes
- Always call this first for coding work. Use the exact `task_id` returned for all later tools; recover with `get_current_coding_task` if missing.

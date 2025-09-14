# Judge Coding Task Completion

## Description
Final validation gate before declaring a task complete. Called when `workflow_guidance.next_tool == "judge_coding_task_completion"`.

{% include 'shared/critical_tool_warnings.md' %}

## Prerequisites
- Plan approved via `judge_coding_plan`, code approved via `judge_code_change`, tests approved via `judge_testing_implementation`

## Args
- `task_id`: string — Task UUID (required)
- `completion_summary`: string — Summary of implemented work (required)
- `requirements_met`: list[string] — Requirements satisfied (required)
- `implementation_details`: string — Key implementation details (required)
- `remaining_work`: list[string] — Open items if any (optional)
- `quality_notes`: string — Quality/standards notes (optional)
- `testing_status`: string — Testing status summary (optional)

## Returns
- Response JSON schema (TaskCompletionResult):
```json
{{ TASK_COMPLETION_RESULT_SCHEMA }}
```

## Notes
- The AI coding assistant MUST NOT present or claim task completion, or provide a final completion summary to the user, without successfully calling this tool and receiving approval.
- Always use the exact `task_id`; if missing due to memory limits, recover it via `get_current_coding_task`.

# Judge Testing Implementation

## Description
Validate test quality, coverage, and execution results after code review is approved. The input MUST include real test evidence (raw test runner output and list of test files). Called when `workflow_guidance.next_tool == "judge_testing_implementation"`.

{% include 'shared/critical_tool_warnings.md' %}

## Args
- `task_id`: string — Task UUID (required)
- `test_summary`: string — Summary of the implemented tests (required)
- `test_files`: list[string] — Paths to created/modified test files (required)
- `test_execution_results`: string — Raw test runner output (required). For example, pytest/jest/mocha/go test/JUnit logs including pass/fail counts.
- `test_coverage_report`: string — Coverage details (optional)
- `test_types_implemented`: list[string] — e.g., unit, integration, e2e (optional)
- `testing_framework`: string — e.g., pytest, jest (optional)
- `performance_test_results`: string — Performance results (optional)
- `manual_test_notes`: string — Manual testing notes (optional)

## Returns
- Response JSON schema (JudgeResponse):
```json
{{ JUDGE_RESPONSE_SCHEMA }}
```

## Notes
- Use after `judge_code_change` is approved. Follow `workflow_guidance.next_tool` for the next step.
- Always use the exact `task_id`; recover it via `get_current_coding_task` if missing.
- If `test_files` is empty or `test_execution_results` does not look like raw runner output, this tool will return `approved: false` and request real evidence (copy/paste the test run output and list the test files).

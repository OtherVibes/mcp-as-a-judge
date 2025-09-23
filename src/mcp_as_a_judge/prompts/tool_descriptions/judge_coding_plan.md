# Judge Coding Plan

## Description
Validate a proposed plan and design against requirements, research needs, and risks. Called when `workflow_guidance.next_tool == "judge_coding_plan"`.

{% include 'shared/critical_tool_warnings.md' %}

## Prerequisites
- Thoroughly analyze requirements, propose a concrete plan, and produce a system design
 - Include a Problem Domain Statement, a Library Selection Map (well-known libraries by purpose, with justifications), and an Internal Reuse Map (existing repo components with paths)

## Human-in-the-Loop (HITL) checks
- If foundational choices are ambiguous or missing (e.g., framework/library, UI vs CLI, web vs desktop, API style, auth, hosting), first call `raise_missing_requirements` to elicit user preferences
- If the plan proposes changing an already understood fundamental choice, call `raise_obstacle` to involve the user’s decision
- These HITL tools do not return `next_tool`; rely on workflow guidance to determine the next tool after elicitation

## Args
- `task_id`: string — Task UUID (required)
- `plan`: string — Detailed implementation plan (required)
- `design`: string — Architecture, components, data flow, key decisions (required)
- `research`: string — Findings and rationale (provide if available)
- `research_urls`: list[string] — URLs for external research (if required)
- `context`: string — Additional project context
- `problem_domain`: string — Concise problem domain statement (optional but recommended)
- `problem_non_goals`: list[string] — Non-goals/out-of-scope items (optional)
- `library_plan`: list[object] — Library Selection Map entries: {purpose, selection, source: internal|external|custom, justification}
- `internal_reuse_components`: list[object] — Internal Reuse Map entries: {path, purpose, notes}
- `design_patterns`: list[object] — Design patterns to be applied: {name, area} (required when current_task_metadata.design_patterns_enforcement=true)
- `identified_risks`: list[string] — Enumerated risks; required when current_task_metadata.risk_assessment_required=true (the server will auto-seed sensible defaults if omitted)
- `risk_mitigation_strategies`: list[string] — Mitigations aligned one-to-one with `identified_risks`

## Returns
- Response JSON schema (JudgeResponse):
```json
{{ JUDGE_RESPONSE_SCHEMA }}
```

## Notes
- Follow `workflow_guidance.next_tool` for the next step. Use the exact `task_id` from `set_coding_task`; recover via `get_current_coding_task` if missing.
 - Plans missing a library selection map and internal reuse map will be rejected.

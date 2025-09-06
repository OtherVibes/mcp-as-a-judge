## Workflow v2: Task Lifecycle with Full Diff Finalization and MCP Approval

### Objectives

- Ensure every user request is analyzed and routed to the correct task path: create, update, or reopen.
- Keep MCP context focused during implementation (per-edit reviews), and provide the full-task git diff only at the end for scope/goal verification.
- Require MCP approval for task finalization, confirming all goals and acceptance criteria are met.

### Glossary

- **Task**: A unit of work tracked from intake to finalization (feature, bug fix, refactor).
- **Create**: Start a new task from a new user request.
- **Update**: Modify an existing in-progress task, adjusting scope or deliverables.
- **Reopen**: Re-activate a previously closed task in response to a new or changed request.
- **Task Brief**: A short MD/YAML document capturing ID, title, context, acceptance criteria, risks, scope, and owner.

## Lifecycle Stages

### 1) Intake & Request Analysis (via set_task)

- Entry: A user submits a request (feature/change/bug).
- Actions:
  - Call `set_task(action=create|update|reopen, user_requirements_raw=<verbatim request>, ...)` to capture the request "as is" and establish/update task state.
  - If requirements are unclear: use `raise_missing_requirements` to elicit details; then call `set_task(action=update)` to persist clarified criteria.
  - If blocked by external dependency/policy: use `raise_obstacle` and record options/decision.
  - Establish or update a `Task Brief` (e.g., `docs/tasks/<TASK_ID>.md`) using data returned by `set_task`.
  - Decide branch and PR conventions: `task/<TASK_ID>-<slug>`; link PR to Task ID.
- Exit: Validated Task Brief; routing decision recorded by `set_task`; branch/PR naming chosen.

### 2) Planning & Design

- Entry: Task Brief ready; high-level scope defined.
- Actions:
  - Author plan, design, and research (prior art, libraries, repo integration).
  - Call `judge_coding_plan` and iterate until approved.
  - Update acceptance criteria and deliverables checklist (tests, docs, migration, perf/security notes).
- Exit: Approved plan/design; implementation checklist established.

### 3) Implementation Loop (Per-Edit Review)

- Entry: Plan/design approved.
- Actions:
  - Implement in small, atomic commits on the task branch.
  - After each file edit, call `judge_code_change` with the specific file content and change description.
  - If the plan materially changes, re-run `judge_coding_plan` to re-approve scope.
  - Keep Task Brief current (noting scope deltas, risks, decisions).
- Exit: All planned changes implemented; tests/docs updated; ready for finalization.

### 4) Finalization Gate — Full-Task Git Diff Verification

- Entry: Task branch is ready for review.
- Actions:
  - Compute the full diff of the task branch vs base (e.g., `main`).
  - For each changed file in the diff, call `judge_code_change` and aggregate results.
  - Enforce acceptance criteria and policies: scope alignment, docs/tests present, lint/security pass, no secrets, no unexplained scope creep.
  - Produce a signed Final Diff Verification Report (machine-readable JSON + human summary) and upload as a PR artifact.
  - If any check fails, return to the Implementation Loop.
- Exit: Final Diff Verification Report status: pass; CI required checks green.

### 5) Final Approval & Close-Out (via judge_task_completion)

- Entry: Diff gate passed and CI checks are green.
- Actions:
  - Call `judge_task_completion(task_id, final_diff_report, user_requirements_raw, acceptance_criteria, artifacts)`.
  - If approved: Merge PR; tag/release as appropriate.
  - If not approved: Follow instructions to remediate or call `set_task(action=reopen)` to reopen.
  - Archive artifacts (Task Brief, plan/design, Final Diff Verification Report) linked to the PR/Task.
- Exit: Task state: done (approved) or reopened.

## Tool-to-Stage Mapping (this repository)

- `set_task`: Intake (create/update/reopen) and whenever requirements are clarified; seeds Task Brief with `user_requirements_raw`.
- `build_workflow`: Orchestrates guidance at each stage.
- `raise_missing_requirements`: Intake and any time ambiguity arises.
- `raise_obstacle`: Any stage; records blockers and resolution decisions.
- `judge_coding_plan`: Start of implementation and whenever the plan changes significantly.
- `judge_code_change`: After each edit; at Finalization Gate across all diff files (aggregated).
- `judge_task_completion`: Final approval at end of the diff gate using the aggregated final diff report.

## Automation & CI Integration

### Branching & PR

- Branch naming: `task/<TASK_ID>-<slug>`.
- Link PRs to the Task ID and include the acceptance criteria in the PR body.

### Final Diff Verification Job (CI)

- Required status check executed on the PR (e.g., GitHub Actions):

```bash
git fetch --no-tags --prune --depth=0 origin
BASE_BRANCH=${{ github.base_ref }}
TARGET=${{ github.sha }}
git diff --name-only origin/${BASE_BRANCH}...${TARGET} > changed_files.txt

# Optional: strict hunk-level diff
git diff --unified=0 origin/${BASE_BRANCH}...${TARGET} > full_diff.patch

# Pseudocode for aggregation (runner step)
python - <<'PY'
import json, os
files = [f.strip() for f in open('changed_files.txt') if f.strip()]
results = []
for path in files:
    # Read file content; skip deletions
    if not os.path.exists(path):
        continue
    content = open(path, 'r', encoding='utf-8', errors='ignore').read()
    # Call MCP judge_code_change via client; collect JSON response
    # response = mcp.judge_code_change(code_change=content, file_path=path, ...)
    # results.append(response)
    pass
aggregate = {
  "summary": {
    "approved": bool(results) and all(r.get('data', {}).get('approved', False) for r in results),
  },
  "files": results,
}
open('final_diff_verification.json', 'w').write(json.dumps(aggregate, indent=2))
PY

# Upload artifact and set status based on aggregate.summary.approved
```

- Make this job a required status check before merge. Combine with CODEOWNERS where appropriate.

- Treat an empty result set as failure to avoid false positives:
  - approved = bool(results) and all(r.get('approved') for r in results)
  - Fail the job if aggregate.approved is false and annotate errors.

## Artifacts & Audit Trail

- Task Brief: `docs/tasks/<TASK_ID>.md` with YAML frontmatter (id, title, context, acceptance_criteria[], risks[], scope, owner).
- Plan/Design/Research bundle: stored in repo (e.g., `docs/tasks/<TASK_ID>/plan.md`).
- Per-edit `judge_code_change` outcomes: optional, can be surfaced in PR comments.
- Final Diff Verification Report: JSON artifact attached to the PR; link referenced in the merge commit message.
- MCP approval record: timestamp, approver identity, and hash of the Final Diff Verification Report.

## Acceptance Criteria

- Scope alignment: All diff changes map to the Task Brief and approved plan; no out-of-scope edits.
- Quality: Lint/tests/security (and secret scans) pass; docs updated or explicit N/A rationale provided.
- Completeness: Acceptance criteria met; edge cases addressed; rollback considerations noted.
- Auditability: Final Diff Verification Report artifact present and referenced in PR.

## Governance & Security

- Use required checks and CODEOWNERS to enforce gates.
- Secrets policy: block merges if any secrets are detected in the diff.
- Risk thresholds: for large or sensitive diffs, require additional review and/or sign-off.

## Rollout Plan

- Phase 1: Adopt for new tasks; document conventions; dry-run diff gate (non-blocking).
- Phase 2: Enable diff gate as a required status; incorporate secret scanning.
- Phase 3: Tune heuristics; add specialized checks (performance, migrations, API stability) where applicable.

## Appendix

### Task Brief Template (YAML frontmatter + MD)

```markdown
---
id: TASK-123
title: Implement X
scope: Add Y to module Z
acceptance_criteria:
  - Criterion 1
  - Criterion 2
risks:
  - Risk A
owner: alice
context:
  - link to design doc
---

Summary and notes here.
```

### References

- Git diff concepts and options: [git diff docs](https://git-scm.com/docs/git-diff)
- Required status checks: [GitHub required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-required-status-checks)
- CODEOWNERS policy: [About CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- Workflow configuration patterns (Jira-style states): [Configure workflows](https://support.atlassian.com/jira-cloud-administration/docs/configure-workflows/)

---

## New Tools and Standard Response Envelope

This workflow introduces new tools and standardizes responses for all tools to include `next_tool` and `instructions` to guide the AI coding assistant on how to prepare for the next call. The `set_task` tool replaces the old commit-driven workflow for state transitions.

### Standard Response Envelope (all tools)

Fields returned by every tool:

- next_tool: string | null — the recommended next tool to call
- instructions: string — concrete preparation steps for the assistant before calling `next_tool`
- blockers: string[] (optional) — items that require user input or environment fixes
- data: object (optional) — tool-specific payload returned for chaining

Example:

```json
{
  "envelope_version": "1.0",
  "next_tool": "judge_coding_plan",
  "instructions": {
    "audience": "machine",
    "rationale": "Prepare planning artifacts for review.",
    "steps": [
      "Draft plan, design, and research",
      "Collect research URLs",
      "Call judge_coding_plan with all inputs"
    ],
    "payload": {
      "expected_inputs": ["plan", "design", "research", "user_requirements", "research_urls?", "context?"]
    }
  },
  "metadata": { "task_id": "TASK-123", "correlation_id": "req-789", "priority": "normal" },
  "blockers": [],
  "data": { "task_id": "TASK-123" }
}
```

### set_task (REPLACES COMMIT WORKFLOW)

Purpose: Canonical entry/update point for task lifecycle. Captures the user request "as is" and sets/updates task state: create/update/reopen.

Inputs:
- action: "create" | "update" | "reopen"
- user_requirements_raw: string — verbatim user request text (exactly as provided)
- related_task_id: string (optional, required for update/reopen when applicable)
- context: string (optional) — links, repo notes, prior artifacts
- acceptance_criteria: string[] (optional) — if provided or elicited
- metadata: object (optional) — labels, priority, owner

Outputs (standard envelope + data):
- next_tool: usually "judge_coding_plan" (for new/changed scope) or "raise_missing_requirements" if unclear
- instructions: how to prepare plan/design/research or what to elicit
- data: { task_id: string, state: string, acceptance_criteria: string[] }

Notes:
- This replaces commit-based state signaling. All state transitions (create/update/reopen) occur through `set_task` calls.
- The Implementation Loop should not rely on commit conventions for workflow control.

#### Envelope Versioning and Metadata

- envelope_version: string (e.g., "1.0")
- metadata (optional):
  - task_id: string
  - correlation_id: string
  - correlation_ts: string (ISO timestamp)
  - priority: "low" | "normal" | "high"
  - final: boolean (true indicates lifecycle termination; requires next_tool = null)

### judge_coding_plan

Purpose: Validate plan/design/research against user requirements and repository context.

Inputs:
- plan: string
- design: string
- research: string
- user_requirements: string — may reference `set_task.user_requirements_raw`
- research_urls: string[] (optional)
- context: string (optional)

Outputs:
- next_tool: "judge_code_change" (start first edit review) or "raise_missing_requirements" for gaps
- instructions: object with audience/rationale/steps/payload describing how to implement the first change and call `judge_code_change`
- terminal: boolean (optional; true only when lifecycle ends)
- blockers: string[] (optional)
- data: { approved: boolean, feedback: string, required_improvements?: string[] }

### judge_code_change

Purpose: Review a single change (per edit) or a file in the final diff.

Inputs:
- code_change: string — exact content or diff hunk
- user_requirements: string — from Task Brief and `set_task`
- file_path: string (optional)
- change_description: string (optional)

Outputs:
- next_tool: usually null (continue edits) or "judge_code_change" for remaining files during finalization
- instructions: object with audience/rationale/steps/payload detailing what to fix before proceeding
- terminal: boolean (optional; true only when lifecycle ends)
- blockers: string[] (optional)
- data: { approved: boolean, feedback: string, required_improvements?: string[] }

### judge_task_completion (NEW)

Purpose: Final gate for the entire task, aggregating full-task git diff results, policy checks, and acceptance criteria.

Inputs:
- task_id: string
- final_diff_report: object — aggregated per-file `judge_code_change` envelopes and CI signals
- user_requirements_raw: string — from `set_task`
- acceptance_criteria: string[]
- artifacts: object (optional) — links to reports, test results

Outputs:
- next_tool: null on success, or "set_task" if reopening due to unmet goals
- instructions: object with audience/rationale/steps/payload for merge/release or remediation
- terminal: boolean (optional; true if approved and lifecycle ends)
- blockers: string[] (optional)
- data: { approved: boolean, feedback: string, required_improvements?: string[] }

### raise_missing_requirements

Purpose: Elicit missing details and clarify acceptance criteria.

Inputs:
- current_request: string — may be `user_requirements_raw`
- identified_gaps: string[]
- specific_questions: string[]

Outputs:
- next_tool: "set_task" (to update task with clarified requirements) or "judge_coding_plan"
- instructions: object with audience/rationale/steps/payload to record clarified criteria and proceed
- terminal: boolean (optional; typically false)
- blockers: string[] (optional)
- data: { clarified_requirements: object }

### raise_obstacle

Purpose: Present options and capture user decision when blocked.

Inputs:
- problem: string
- research: string
- options: string[]

Outputs:
- next_tool: depends on selected option (e.g., "set_task", "judge_coding_plan")
- instructions: object with audience/rationale/steps/payload for actions to resolve the blocker
- terminal: boolean (optional; typically false)
- blockers: string[] (optional)
- data: { decision: string, rationale: string }

### build_workflow

Purpose: Provide step-by-step guidance and tool ordering for the current stage.

Inputs:
- task_description: string
- context: string (optional)

Outputs:
- next_tool: recommended next tool per analysis
- instructions: object with audience/rationale/steps/payload for preparation and prerequisites
- terminal: boolean (optional; typically false)
- blockers: string[] (optional)
- data: { stage: string, rationale: string }

#### Canonical final_diff_report structure (example)

```json
{
  "summary": {
    "approved": true,
    "ci_status": "success",
    "secret_scan": "clean",
    "tests": { "passed": 128, "failed": 0, "coverage": 0.86 }
  },
  "files": [
    {
      "next_tool": null,
      "instructions": {"audience":"machine","rationale":"","steps":[],"payload":{}},
      "blockers": [],
      "data": {
        "approved": true,
        "feedback": "OK",
        "required_improvements": []
      },
      "metadata": { "file_path": "src/app.py" }
    }
  ],
  "artifacts": {
    "diff_hunks": "artifact://full_diff.patch",
    "report_link": "artifact://final_diff_verification.json"
  }
}
```

#### Expanded final_diff_report structure

```json
{
  "task_id": "TASK-123",
  "generated_at": "2025-09-06T12:00:00Z",
  "summary": {
    "approved": true,
    "ci_status": "success",
    "secret_scan": "clean",
    "tests": { "passed": 128, "failed": 0, "coverage": 0.86 },
    "message": "All files approved; no policy violations detected"
  },
  "stats": { "total_files": 4, "total_additions": 220, "total_deletions": 12 },
  "files": [
    {
      "path": "src/app.py",
      "change_type": "modified",
      "additions": 42,
      "deletions": 3,
      "hunks": "@@ -10,0 +11,5 @@ ...",
      "review": {
        "envelope_version": "1.0",
        "next_tool": null,
        "instructions": "",
        "blockers": [],
        "data": { "approved": true, "feedback": "OK", "required_improvements": [] },
        "metadata": { "file_path": "src/app.py", "correlation_ts": "2025-09-06T11:59:01Z" }
      }
    }
  ],
  "breaking_changes": [],
  "risks": ["Touches auth flows"],
  "follow_ups": ["Add load test"],
  "artifacts": {
    "diff_hunks": "artifact://full_diff.patch",
    "report_link": "artifact://final_diff_verification.json"
  }
}
```

---

## Tool Registry and Validation

Valid tool identifiers (registry):

- set_task
- build_workflow
- raise_missing_requirements
- raise_obstacle
- judge_coding_plan
- judge_code_change
- judge_task_completion

Rules:

- next_tool must be one of the above or null.
- If an unknown next_tool is proposed, return an error with code "UNKNOWN_TOOL" and the allowed list.
- When lifecycle completes, set next_tool = null and metadata.final = true.

---

## Detailed Tool Payloads and Examples

### set_task

Request:

```json
{
  "action": "create|update|reopen",
  "user_requirements_raw": "<verbatim user text>",
  "related_task_id": "TASK-123" ,
  "context": "links or notes",
  "acceptance_criteria": ["..."],
  "metadata": { "owner": "alice", "priority": "high" }
}
```

Response:

```json
{
  "envelope_version": "1.0",
  "next_tool": "judge_coding_plan",
  "instructions": "Draft plan/design/research referencing the captured requirements, then call judge_coding_plan.",
  "metadata": { "task_id": "TASK-456", "correlation_id": "req-001" },
  "blockers": [],
  "data": { "status": "ok", "task_id": "TASK-456", "state": "open", "acceptance_criteria": ["..."] }
}
```

Failure example:

```json
{
  "envelope_version": "1.0",
  "next_tool": "raise_missing_requirements",
  "instructions": "Elicit missing acceptance criteria: performance thresholds and security requirements.",
  "metadata": { "correlation_id": "req-002" },
  "blockers": ["Acceptance criteria missing"],
  "data": { "status": "error", "error": { "code": "MISSING_FIELDS", "fields": ["acceptance_criteria"] } }
}
```

### judge_task_completion

Request:

```json
{
  "task_id": "TASK-456",
  "final_diff_report": { /* see canonical structure */ },
  "user_requirements_raw": "<verbatim user text>",
  "acceptance_criteria": ["..."],
  "artifacts": { "ci_run": "https://..." }
}
```

Success response:

```json
{
  "envelope_version": "1.0",
  "next_tool": null,
  "instructions": "Proceed to merge and tag release.",
  "metadata": { "task_id": "TASK-456", "final": true },
  "blockers": [],
  "data": { "approved": true, "result": "pass", "confidence": 0.92, "feedback": "All goals achieved." }
}
```

Failure response:

```json
{
  "envelope_version": "1.0",
  "next_tool": "set_task",
  "instructions": "Reopen task with updated acceptance criteria to cover missing negative tests.",
  "metadata": { "task_id": "TASK-456" },
  "blockers": ["Missing negative-path tests"],
  "data": { "approved": false, "result": "fail", "reasons": ["Coverage drop > threshold"], "required_improvements": ["Add negative tests"] }
}
```

---

## CI Aggregation with Envelope and Registry

Validator and aggregator (pseudocode):

```python
REGISTRY = {"set_task","build_workflow","raise_missing_requirements","raise_obstacle","judge_coding_plan","judge_code_change","judge_task_completion"}

def validate_envelope(env: dict) -> None:
    assert env.get("envelope_version") == "1.0"
    nt = env.get("next_tool")
    assert (nt is None) or (nt in REGISTRY)

def aggregate(file_results: list[dict]) -> dict:
    # optional: collapse duplicates by latest correlation_ts
    by_path = {}
    for r in file_results:
        validate_envelope(r)
        path = r.get("metadata", {}).get("file_path", "<unknown>")
        ts = r.get("metadata", {}).get("correlation_ts", "")
        prev = by_path.get(path)
        if not prev or ts > prev.get("metadata", {}).get("correlation_ts", ""):
            by_path[path] = r
    results = list(by_path.values())
    approved = bool(results) and all(x.get("data", {}).get("approved", False) for x in results)
    return {"summary": {"approved": approved}, "files": results}
```

---

## Commit Workflow Replacement

`set_task` replaces the commit-driven workflow for signaling task state transitions. Remove assumptions that commit messages or branching alone control workflow progression. The authoritative lifecycle transitions are:

- set_task(action=create) → create new Task Brief with `user_requirements_raw` and initial acceptance criteria
- set_task(action=update) → update Task Brief and re-run planning if scope changed
- set_task(action=reopen) → reopen a closed task, preserving artifacts and updating acceptance criteria

Implementation Loop amendments:

- Remove guidance about “keeping commits referencing Task ID and scope” as a control signal.
- Continue to recommend small, atomic changes for readability, but rely on `set_task` for lifecycle transitions.

---

## Diagrams

### Old Workflow (High-Level)

```mermaid
flowchart TD
  A[User Request] --> B[build_workflow]
  B --> C[Plan/Design/Research]
  C --> D[judge_coding_plan]
  D -- Approved --> E[Implementation]
  D -- Revisions --> C
  E --> F[judge_code_change (per edit)]
  F -- Iterate --> E
  F --> G[PR Review/Merge]
```

### New Workflow (With set_task & Final Judge)

```mermaid
flowchart TD
  A[User Request] --> S[set_task(create/update/reopen)\nuser_requirements_raw]
  S --> BW[build_workflow]
  BW --> P[Plan/Design/Research]
  P --> JCP[judge_coding_plan]
  JCP -- Approved --> I[Implementation Loop]
  JCP -- Clarify --> RMR[raise_missing_requirements]
  RMR --> S
  I --> JCC1[judge_code_change (per edit)]
  JCC1 --> I
  I --> D1[Compute Full Git Diff]
  D1 --> JCC2[judge_code_change (per file in diff)]
  JCC2 --> FR[Aggregate Final Diff Report]
  FR --> JTC[judge_task_completion]
  JTC -- Approved --> M[Merge/Release]
  JTC -- Reopen --> S
  S ---- If Blocked ----> RO[raise_obstacle]
  RO --> S
```



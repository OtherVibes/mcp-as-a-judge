# MCP as a Judge - Simplified Workflow Instructions

## Overview

The MCP as a Judge system uses a **simplified state machine workflow** where each tool response includes a `next_tool` field that determines the next step. This provides predictable, deterministic workflow progression.

## Core Workflow States

```
CREATED → PLANNING → PLAN_APPROVED → IMPLEMENTING → REVIEW_READY → TESTING → COMPLETED
```

## Workflow Progression

### 1. Task Creation (CREATED)
- **Tool**: `set_coding_task` 
- **Next**: `judge_coding_plan`
- **Action**: Create task metadata and transition to planning

### 2. Planning Phase (PLANNING)
- **Tool**: `judge_coding_plan`
- **Next**: Implementation phase (if approved) or `None` (if needs revision)
- **Action**: Validate plan and design with conditional research, internal analysis, and risk assessment

### 3. Implementation & Testing (PLAN_APPROVED → IMPLEMENTING)
- **Action**: Implement ALL code AND write tests, ensure tests are passing with good coverage
- **Requirement**: Code and tests must be complete and passing before code review

### 4. Code Review (IMPLEMENTING → REVIEW_READY)
- **Tool**: `judge_code_change`
- **Next**: `judge_testing_implementation` (if approved) or fix code and re-test (if needs fixes)
- **Action**: Review ONLY implementation code changes (not tests), validate code quality and logic

### 5. Test Review (REVIEW_READY → TESTING)
- **Tool**: `judge_testing_implementation`
- **Next**: `judge_coding_task_completion` (if approved) or fix tests and re-review (if needs fixes)
- **Action**: Review test results, coverage, and testing approach quality

### 6. Task Completion (TESTING → COMPLETED)
- **Tool**: `judge_coding_task_completion`
- **Next**: `None` (workflow complete) or previous tools (if needs more work)
- **Action**: Final validation and task completion

## Key Principles

### 1. Follow the next_tool Field
**ALWAYS** call the tool specified in the `next_tool` field from the previous response.

### 2. State-Driven Workflow
Each tool automatically transitions the task to the appropriate state based on the validation result.

### 3. Comprehensive Validation
- **Planning**: Validate research, design, and implementation approach
- **Testing**: Validate that tests are written and passing
- **Code Review**: Review ALL modified files as a complete solution
- **Completion**: Ensure all requirements are met

### 4. Error Handling
If a tool returns `approved: false`, address the `required_improvements` before proceeding.

## Agent Instructions

### After set_coding_task
1. **Always call** `judge_coding_plan` next
2. **Prepare**: Research, design, and detailed implementation plan
3. **Include**: Research URLs, system design, and comprehensive plan

### After judge_coding_plan (if approved)
1. **Implement ALL code AND write tests**
2. **Ensure tests are passing with good coverage**
3. **Then call** `judge_code_change` for code review

### Before judge_code_change
1. **Requirement**: ALL implementation code AND tests must be written and passing
2. **Prepare**: Complete implementation with passing tests
3. **Include**: ONLY implementation code changes (not test files) for review

**CRITICAL**: judge_code_change should ONLY be called when:
- ALL implementation work is finished
- ALL tests are written and passing
- Ready for code review (implementation only, not tests)

### After judge_code_change (if approved)
1. **Always call** `judge_testing_implementation` next
2. **Prepare**: Test results, coverage reports, test quality analysis
3. **Include**: Test execution results, coverage metrics, testing approach validation

### After judge_testing_implementation (if approved)
1. **Always call** `judge_coding_task_completion` next
2. **Prepare**: Complete implementation summary
3. **Include**: Requirements met, implementation details, completion summary

### After judge_coding_task_completion (if approved)
1. **Workflow Complete**: Task is finished when judge_coding_task_completion is approved
2. **Final State**: Task transitions to COMPLETED state
3. **No Further Tools**: No additional tools needed in the main workflow

### If Any Tool Returns approved: false
1. **Address** all items in `required_improvements`
2. **Resubmit** to the same tool with fixes
3. **Continue** the workflow once approved

## Common Workflow Patterns

### Happy Path
```
set_coding_task → judge_coding_plan → [implement code + write tests] → judge_code_change → judge_testing_implementation → judge_coding_task_completion → DONE
```

### With Code Review Revisions
```
set_coding_task → judge_coding_plan → [implement + test] → judge_code_change (needs fixes) →
[fix code + adapt tests + re-test] → judge_code_change (approved) → judge_testing_implementation → judge_coding_task_completion → DONE
```

### With Test Review Revisions
```
set_coding_task → judge_coding_plan → [implement + test] → judge_code_change (approved) →
judge_testing_implementation (needs fixes) → [improve tests + re-test] → judge_testing_implementation (approved) → judge_coding_task_completion → DONE
```

### Error Recovery
```
Any tool → approved: false → Fix required_improvements → Resubmit to same tool → Continue workflow
```

## Important Notes

1. **No Skipping**: Always follow the prescribed tool sequence
2. **Complete Preparation**: Ensure all prerequisites are met before calling each tool
3. **Address Feedback**: Always fix issues before proceeding
4. **State Awareness**: Tools automatically manage state transitions
5. **Comprehensive Approach**: Each validation covers the complete scope (not partial)

This simplified workflow ensures predictable, reliable task progression while maintaining comprehensive validation at each stage.

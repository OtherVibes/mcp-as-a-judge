# Dynamic Workflow System

## Overview

The MCP as a Judge system uses a **dynamic workflow** where each tool response includes `workflow_guidance` that determines the next step. This replaces static tool sequences with intelligent, context-aware navigation.

## Core Principle

**ALWAYS follow the `workflow_guidance.next_tool` field from tool responses.**

Every tool response includes:
```json
{
  "workflow_guidance": {
    "next_tool": "tool_name_to_call_next",
    "reasoning": "Why this tool should be called next",
    "preparation_needed": ["What to prepare before calling"],
    "guidance": "Detailed instructions for the next step"
  }
}
```

## Dynamic Workflow Pattern

```
User Request → set_coding_task → workflow_guidance.next_tool → workflow_guidance.next_tool → ... → Task Complete
```

**Key Points:**
- Each tool determines what should happen next based on current context
- No fixed sequences - the workflow adapts to the situation
- Trust the guidance - each tool has full context and makes intelligent decisions
- The workflow can branch, loop, or skip steps as needed

## Typical Workflow Paths

### New Task Creation (with Testing)
```
User Request → set_coding_task → judge_coding_plan → judge_code_change → judge_testing_implementation → judge_coding_task_completion
```

### Task with Issues
```
User Request → set_coding_task → judge_coding_plan (rejected) → (fix plan) → judge_coding_plan (approved) → ...
```

### Multiple Files with Testing
```
... → judge_code_change (file1) → judge_code_change (file2) → judge_testing_implementation → judge_coding_task_completion
```

### Iterative Development with Testing
```
... → judge_code_change → judge_code_change → judge_testing_implementation → judge_coding_task_completion
```

### Testing Iteration
```
... → judge_testing_implementation (failed) → (fix tests) → judge_testing_implementation (passed) → judge_coding_task_completion
```

### Complex Workflow with Testing
```
... → judge_code_change → judge_testing_implementation → judge_code_change (fix) → judge_testing_implementation → judge_coding_task_completion
```

## Workflow Guidance Fields

### `next_tool`
- **Purpose**: Specifies exactly which tool to call next
- **Values**: Tool name (e.g., "judge_coding_plan") or `null` if workflow complete
- **Usage**: Always call this tool next, don't guess or assume

### `reasoning`
- **Purpose**: Explains why this tool should be called next
- **Usage**: Provides context for understanding the workflow decision

### `preparation_needed`
- **Purpose**: Lists what should be prepared before calling the next tool
- **Usage**: Follow these steps to ensure the next tool call will be successful

### `guidance`
- **Purpose**: Detailed instructions for the next step
- **Usage**: Provides specific guidance on how to proceed

## Best Practices

### ✅ DO
- Always check `workflow_guidance.next_tool` in every tool response
- Follow the preparation steps in `preparation_needed`
- Read and follow the detailed `guidance`
- Trust the dynamic workflow - it adapts to your specific situation
- Use the same `task_id` throughout the entire workflow
- Ensure the `task_id` is the exact UUID returned by `set_coding_task` (never invent values like `535`). If you lose it, call `get_current_coding_task` to recover.

### ❌ DON'T
- Assume a fixed sequence of tools
- Skip the workflow guidance and call tools in a predetermined order
- Ignore the `preparation_needed` steps
- Call tools without checking if they're the recommended next step
- Start new workflows without calling `set_coding_task` first
- Invent or transform the `task_id`; if lost, call `get_current_coding_task` to recover the last active task. Only call `set_coding_task` to create a brand new task.

## Error Recovery

If a tool fails or returns unexpected results:
1. Check the `workflow_guidance` in the response
2. Follow the recommended next steps
3. The workflow system will guide you to recovery actions
4. Don't try to fix issues by calling random tools

## State Awareness

The workflow system is aware of:
- Current task state (CREATED, PLANNING, IMPLEMENTING, TESTING, etc.)
- Files that have been modified and approved
- Test files that have been created and their status
- Test coverage and execution results
- Previous validation results
- Conversation history and context
- User requirements and task progress

This awareness enables intelligent decisions about what should happen next.

## Integration with Task States

The workflow guidance considers task states:
- **CREATED**: Typically guides to planning phase
- **PLANNING**: Guides to plan validation
- **PLAN_APPROVED**: Guides to implementation
- **IMPLEMENTING**: Guides to code review, continued implementation, or testing
- **TESTING**: Guides to test validation, test fixes, or review readiness
- **REVIEW_READY**: Guides to final completion validation
- **COMPLETED**: Workflow complete

## File Tracking Integration

The system tracks modified files and can:
- Guide to testing validation when implementation is complete
- Guide to completion when all files are approved and tested
- Recommend additional file reviews if needed
- Transition between implementation, testing, and review phases

## Conclusion

The dynamic workflow system provides intelligent, context-aware guidance that adapts to your specific coding task. By following the `workflow_guidance.next_tool` field, you ensure optimal workflow progression and successful task completion.

**Remember: Trust the workflow guidance - it knows the full context and will guide you to success.**

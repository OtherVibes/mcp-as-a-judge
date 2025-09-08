# Set Coding Task

**MANDATORY FIRST STEP**: This tool MUST be called explicitly after every user request that requires coding work.

Create or update coding task metadata with enhanced task-centric workflow management.

## Purpose

This tool creates new coding tasks or updates existing ones, providing intelligent workflow guidance and state management. It serves as the **mandatory entry point** for all coding workflows with enhanced task-centric capabilities.

## When to Call This Tool

**ALWAYS call this tool first when:**
- User requests any coding, development, or implementation work
- User asks to build, create, modify, or fix code
- User requests features, bug fixes, or code improvements
- User asks for code reviews, refactoring, or optimization
- User requests API development, database changes, or system modifications
- ANY request that involves writing, editing, or analyzing code

**Do NOT proceed with coding work without calling this tool first.**

## Dynamic Workflow System

```
User Coding Request → set_coding_task (REQUIRED) → Follow workflow_guidance.next_tool → Continue Dynamic Workflow
```

**Critical Workflow Rules:**
1. **ALWAYS call set_coding_task FIRST** for any coding request
2. **NEVER start coding** without calling this tool first
3. **Follow the workflow_guidance.next_tool** field for dynamic navigation
4. **Use workflow_guidance.preparation_needed** and **guidance** for context
5. **Each tool response contains next_tool** - follow the dynamic workflow chain
6. **Update task state** as work progresses using this tool

## Key Features

- **Task Creation**: Auto-generates immutable task_id (UUID) for new coding tasks
- **Task Updates**: Updates existing tasks using immutable task_id as primary key
- **State Management**: Manages TaskState transitions with validation
- **Workflow Guidance**: Provides intelligent next steps using LLM-driven guidance
- **Memory Integration**: Uses task_id as primary key for conversation history storage

## Parameters

### Required for New Tasks
- `user_request`: Original user request for context
- `task_name`: Human-readable slug (e.g., "implement-user-auth")
- `task_title`: Display title (e.g., "Implement User Authentication")
- `task_description`: Detailed coding task description

### For Updating Existing Tasks
- `task_id`: Immutable task UUID (required when updating existing task)
- `user_requirements`: Updated coding requirements (optional)
- `state`: Updated TaskState (optional, validated against allowed transitions)

### Optional
- `tags`: List of coding-related tags

## Task States

The tool manages coding tasks through well-defined states:

- **CREATED**: Task just created, needs planning
- **PLANNING**: Planning phase in progress
- **PLAN_APPROVED**: Plan validated and approved
- **IMPLEMENTING**: Implementation phase in progress
- **TESTING**: Testing phase in progress
- **REVIEW_READY**: All tests passing, ready for final review
- **COMPLETED**: Task completed successfully
- **BLOCKED**: Task blocked by external dependencies
- **CANCELLED**: Task cancelled

## State Transitions

Valid state transitions are enforced:
- CREATED → PLANNING, BLOCKED, CANCELLED
- PLANNING → PLAN_APPROVED, CREATED, BLOCKED, CANCELLED
- PLAN_APPROVED → IMPLEMENTING, PLANNING, BLOCKED, CANCELLED
- IMPLEMENTING → IMPLEMENTING, TESTING, REVIEW_READY, PLAN_APPROVED, BLOCKED, CANCELLED
- TESTING → TESTING, REVIEW_READY, IMPLEMENTING, BLOCKED, CANCELLED
- REVIEW_READY → COMPLETED, TESTING, IMPLEMENTING, BLOCKED, CANCELLED
- COMPLETED → CANCELLED (only cancellation allowed)
- BLOCKED → Any previous state, CANCELLED
- CANCELLED → (no transitions allowed)

## Response

Returns `TaskAnalysisResult` containing:
- `action`: "created" or "updated"
- `context_summary`: Summary of the task context
- `current_task_metadata`: Complete current task metadata
- `workflow_guidance`: LLM-generated next steps and instructions

## Usage Examples

### Mandatory First Call for Any Coding Request

**User Request**: "I need to add user authentication to my app"

**Step 1 - ALWAYS call set_coding_task first:**
```python
result = await set_coding_task(
    user_request="I need to add user authentication to my app",
    task_name="implement-user-auth",
    task_title="Implement User Authentication",
    task_description="Add secure user authentication with JWT tokens",
    user_requirements="Users should be able to register, login, and logout securely",
    tags=["authentication", "security", "backend"]
)
```

**Step 2 - Follow the dynamic workflow_guidance:**
```python
# Result contains workflow_guidance with next_tool and instructions
next_tool = result.workflow_guidance.next_tool  # e.g., "judge_coding_plan"
preparation = result.workflow_guidance.preparation_needed  # What to prepare
instructions = result.workflow_guidance.guidance  # Detailed next steps

# ALWAYS call the next_tool specified in the response
# Each tool will return its own workflow_guidance for the next step
```

### Update Existing Task
```python
result = await set_coding_task(
    user_request="Update requirements for authentication task",
    task_name="implement-user-auth",
    task_title="Implement User Authentication",
    task_description="Add secure user authentication with JWT tokens",
    task_id="550e8400-e29b-41d4-a716-446655440000",
    user_requirements="Updated: Add password reset functionality",
    state=TaskState.PLANNING
)
```

## ⚠️ CRITICAL WORKFLOW REQUIREMENTS

**MANDATORY DYNAMIC WORKFLOW PATTERN:**
```
Every Coding Request → set_coding_task → workflow_guidance.next_tool → workflow_guidance.next_tool → ... → Complete Task
```

**❌ NEVER DO THIS:**
- Start coding without calling set_coding_task first
- Skip this tool for "simple" coding requests
- Assume the task context from previous conversations
- Ignore the workflow_guidance.next_tool field
- Call tools in a fixed sequence instead of following dynamic guidance

**✅ ALWAYS DO THIS:**
- Call set_coding_task immediately after any coding request
- Follow the workflow_guidance.next_tool recommendation from EVERY tool response
- Use workflow_guidance.preparation_needed and guidance for context
- Update task state as work progresses
- Use the returned task_id for all subsequent operations
- Trust the dynamic workflow - each tool knows what should come next

## Integration

- **Memory Storage**: Uses task_id as primary key for conversation history
- **Workflow Guidance**: Integrates with shared `calculate_next_stage` method
- **State Validation**: Enforces valid state transitions
- **Requirements Tracking**: Maintains history of requirement changes

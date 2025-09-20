# Update Plan with LLM Feedback

## Description
**PLAN REFINEMENT TOOL**: Update implementation plans based on LLM technical feedback and validation results. This tool incorporates LLM suggestions while preserving user requirements and intent.

## Args
- `task_id`: string — Task ID for context tracking
- `original_plan`: string — The original implementation plan that was rejected by LLM
- `llm_feedback`: string — Detailed feedback from LLM technical validation
- `required_improvements`: list[string] — Specific improvements required by LLM
- `technical_concerns`: list[string] — Technical concerns raised by LLM validation

## Returns
- `PlanUpdateResult`: Structured result containing updated plan with LLM improvements incorporated

## Usage Context
- **TRIGGERED BY LLM REJECTION**: Called when judge_coding_plan rejects a user-approved plan
- **PRESERVES USER INTENT**: Maintains all user requirements while addressing technical issues
- **LLM-POWERED UPDATES**: Uses MCP sampling to intelligently incorporate feedback
- **TECHNICAL IMPROVEMENT**: Addresses architecture, patterns, and best practice concerns
- **VERSION TRACKING**: Creates Plan B, Plan C, etc. with clear version information
- **SAVES TO DATABASE**: Plan update interactions are saved for context
- **STATE MANAGEMENT**: Returns task to REQUIREMENTS_FEEDBACK for user re-approval
- **DUAL APPROVAL PREP**: Prepares updated plan for user re-approval before LLM re-validation
- **COLLABORATIVE REFINEMENT**: Enables iterative improvement between user and LLM

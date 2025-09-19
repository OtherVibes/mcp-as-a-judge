# Get Enhanced User Feedback

## Description
**MANDATORY FIRST STEP**: Comprehensive requirements elicitation including documentation, success criteria, environment context, and testing requirements. This enhanced brainstorming phase ensures thorough understanding before development begins.

## Args
- `current_request`: string — Current understanding of the user's request
- `identified_gaps`: list[string] — Specific requirement gaps that need clarification
- `specific_questions`: list[string] — Targeted questions to ask the user
- `decision_areas`: list[string] — Fundamental technical decisions that need user input (e.g., programming_language, framework, database_type, ui_type, api_style, authentication, hosting, deployment)
- `suggested_options`: list[dict] — Suggested options with pros/cons for each decision area (format: {"area": "framework", "options": [{"name": "FastAPI", "pros": ["Fast", "Modern"], "cons": ["Learning curve"]}, ...]})
- `repository_analysis`: string — Analysis of current repository to inform language/framework decisions
- `documentation_requests`: list[string] — Requests for relevant documentation, APIs, examples, or reference materials
- `success_criteria_questions`: list[string] — Questions to define clear "done" criteria and acceptance tests
- `environment_context_questions`: list[string] — Questions about development environment, deployment constraints, performance requirements
- `testing_requirements_questions`: list[string] — Questions about testing approach, coverage expectations, test types needed
- `task_id`: string — Task ID for context tracking

## Returns
- `ElicitationResult`: Structured result containing user responses, clarified requirements, and technical decisions

## Usage Context
- **ALWAYS CALLED FIRST** for ALL tasks regardless of size (XS, S, M, L, XL)
- **MANDATORY BRAINSTORMING PHASE** - never skip this step
- Called immediately after task creation to gather detailed requirements
- Transitions task from CREATED to REQUIREMENTS_FEEDBACK state
- Uses MCP elicitation capabilities when available, falls back to structured prompts
- Captures all user feedback for integration into task requirements
- Saves technical decisions to task metadata for use throughout workflow
- Analyzes repository context to inform technology stack decisions
- Part of the brainstorming phase - interactions are saved to database for LLM context
- Supports language-agnostic approach with generic best practices guidance

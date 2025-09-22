# Workflow Guidance Exposure to Plan System Prompt

This document demonstrates how the enhanced workflow guidance system exposes structured guidance to the plan system prompt, enabling better preparation for plan judgment.

## Overview

The workflow guidance system now provides comprehensive structured information to the plan system prompt, including:

- **Next Tool**: What tool should be called next
- **Reasoning**: Why this tool is recommended
- **Preparation Required**: Specific preparation steps needed
- **Required Plan Fields**: Detailed field specifications with types, requirements, and conditions
- **Detailed Guidance**: Comprehensive guidance text

## Example Workflow Guidance Structure

```json
{
  "next_tool": "judge_coding_plan",
  "reasoning": "Plan needs validation before implementation can begin",
  "preparation_needed": [
    "Prepare comprehensive design document with architecture details",
    "Define library selection map with purpose, selection, source, and justification",
    "Identify internal reuse components from existing codebase",
    "Assess risks and define mitigation strategies"
  ],
  "plan_required_fields": [
    {
      "name": "plan",
      "type": "string",
      "required": true,
      "description": "Detailed implementation plan with step-by-step approach"
    },
    {
      "name": "design",
      "type": "string", 
      "required": true,
      "description": "Architecture and component design documentation"
    },
    {
      "name": "library_plan",
      "type": "list[dict]",
      "required": true,
      "description": "Library selection map with purpose, selection, source, justification"
    },
    {
      "name": "design_patterns",
      "type": "list[dict]",
      "required": true,
      "conditional_on": "design_patterns_enforcement",
      "description": "Design patterns to be applied: {name, area}"
    },
    {
      "name": "identified_risks",
      "type": "list[string]",
      "required": true,
      "conditional_on": "risk_assessment_required",
      "description": "Enumerated risks that could impact the implementation"
    }
  ],
  "guidance": "Create comprehensive plan addressing all required fields and ensure alignment with task requirements. Focus on reusing existing components and well-known libraries."
}
```

## How It Works

### 1. Workflow Guidance Generation

When `calculate_next_stage` is called, it generates structured workflow guidance that includes:
- Dynamic field requirements based on task metadata
- Conditional requirements (e.g., design patterns only when enforcement is enabled)
- Comprehensive preparation instructions

### 2. Guidance Extraction

The `_extract_latest_workflow_guidance` function:
- Searches conversation history for the most recent workflow guidance
- Returns the full structured guidance object (not just the text)
- Handles malformed data gracefully

### 3. Guidance Formatting for System Prompt

The plan evaluation system formats the structured guidance into a comprehensive text block:

```markdown
**Next Tool:** judge_coding_plan
**Reasoning:** Plan needs validation before implementation can begin
**Preparation Required:**
- Prepare comprehensive design document with architecture details
- Define library selection map with purpose, selection, source, and justification
- Identify internal reuse components from existing codebase
- Assess risks and define mitigation strategies
**Required Plan Fields:**
- **plan** (string) [REQUIRED]: Detailed implementation plan with step-by-step approach
- **design** (string) [REQUIRED]: Architecture and component design documentation
- **library_plan** (list[dict]) [REQUIRED]: Library selection map with purpose, selection, source, justification
- **design_patterns** (list[dict]) [REQUIRED] [Conditional on: design_patterns_enforcement]: Design patterns to be applied: {name, area}
- **identified_risks** (list[string]) [REQUIRED] [Conditional on: risk_assessment_required]: Enumerated risks that could impact the implementation
**Detailed Guidance:** Create comprehensive plan addressing all required fields and ensure alignment with task requirements. Focus on reusing existing components and well-known libraries.
```

### 4. Plan System Prompt Integration

The plan system prompt uses this formatted guidance to:
- **Field Validation**: Validate only the exact fields specified in "Required Plan Fields"
- **Preparation Alignment**: Ensure the plan addresses all "Preparation Required" items
- **Tool Readiness**: Verify the plan is prepared for the "Next Tool"
- **Conditional Requirements**: Apply conditional field requirements only when conditions are met
- **Scope Adherence**: Avoid applying generic software engineering principles beyond the guidance

## Benefits

### 1. Precise Evaluation Criteria
- The judge only evaluates based on explicitly specified requirements
- No additional requirements are imposed beyond what's in the guidance
- Conditional fields are only required when their conditions are met

### 2. Better AI Assistant Preparation
- The AI assistant receives detailed field specifications
- Type information helps with proper data structure preparation
- Conditional requirements are clearly marked

### 3. Consistent Workflow
- The guidance ensures the plan is prepared for the next workflow step
- Preparation requirements align with what the judge will evaluate
- Reasoning provides context for why specific fields are needed

### 4. Reduced Validation Failures
- Clear field specifications reduce schema validation errors
- Conditional logic prevents unnecessary field requirements
- Comprehensive guidance reduces missing information

## Example Usage

When an AI coding assistant receives workflow guidance recommending `judge_coding_plan`, it can:

1. **Review Required Fields**: Check exactly which fields are required and their types
2. **Understand Conditions**: See which fields are conditional and when they apply
3. **Follow Preparation**: Address each preparation requirement systematically
4. **Align with Reasoning**: Understand why the plan validation is needed
5. **Prepare for Next Step**: Ensure the plan enables the next workflow step

This structured approach significantly improves the success rate of plan validation and reduces back-and-forth iterations between the AI assistant and the judge system.

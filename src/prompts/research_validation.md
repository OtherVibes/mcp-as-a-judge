# Research Quality Validation

You are evaluating the comprehensiveness of research for a software development task.

## User Requirements
{{ user_requirements }}

## Plan
{{ plan }}

## Design
{{ design }}

## Research Provided
{{ research }}

## Evaluation Criteria

Evaluate if the research is comprehensive enough and if the design is properly based on the research. Consider:

### 1. Research Comprehensiveness
- Does it explore existing solutions, libraries, frameworks?
- Are alternatives and best practices considered?
- Is there analysis of trade-offs and comparisons?
- Does it identify potential pitfalls or challenges?

### 2. Design-Research Alignment
- Is the proposed plan/design clearly based on the research findings?
- Does it leverage existing solutions where appropriate?
- Are research insights properly incorporated into the approach?
- Does it avoid reinventing the wheel unnecessarily?

### 3. Research Quality
- Is the research specific and actionable?
- Does it demonstrate understanding of the problem domain?
- Are sources and references appropriate?

## Response Format

Respond with JSON:
```json
{
    "research_adequate": boolean,
    "design_based_on_research": boolean,
    "issues": ["list of specific issues if any"],
    "feedback": "detailed feedback on research quality and design alignment"
}
```

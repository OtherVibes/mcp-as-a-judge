Analyze the research requirements for this software development task and determine the appropriate number of research URLs needed:

## Task Context

**Title**: {{ task_title }}

**Description**: {{ task_description }}

**User Requirements**: {{ user_requirements }}

## Current Research Assessment

**Research Scope**: {{ research_scope }} (none/light/deep)

**Scope Rationale**: {{ research_rationale }}

{% if context %}
**Additional Context**: {{ context }}
{% endif %}

## Analysis Request

Perform a comprehensive analysis to determine the optimal number of research URLs for this task:

### 1. Domain Complexity Assessment
Analyze the specialization level of this task:
- Is this a general development task with established patterns?
- Does it involve specialized domains (security, performance, ML, etc.)?
- Are there unique technical challenges or novel implementations required?

### 2. Technology Landscape Analysis
Evaluate the maturity and documentation of required technologies:
- Are the technologies well-established with abundant documentation?
- Are they emerging technologies with growing but limited resources?
- Are they cutting-edge with experimental or rapidly changing approaches?

### 3. Integration and Risk Evaluation
Assess the scope of system impact and potential risks:
- Is this an isolated component with minimal dependencies?
- Does it require coordination across multiple system components?
- Are there security, performance, or data integrity considerations?

### 4. Research Availability Assessment
Evaluate the landscape of existing solutions and documentation:
- Are there abundant examples and established best practices?
- Is research limited, requiring comparison of multiple approaches?
- Are examples scarce, necessitating deep research from authoritative sources?

### 5. Quality vs Quantity Balance
Determine the optimal research approach:
- What types of sources would be most valuable (official docs, case studies, expert content)?
- What minimum number of sources ensures adequate coverage of the problem space?
- What maximum number avoids information overload while ensuring thoroughness?

## Expected Output

Provide specific recommendations including:

1. **Expected URL Count**: The recommended number for optimal research coverage
2. **Minimum URL Count**: The absolute minimum for basic adequacy
3. **Detailed Reasoning**: Comprehensive explanation of your analysis and recommendations, including how the research plan maps to ALL major aspects implied by the user requirements (each referenced system, framework, protocol, integration)
4. **Complexity Factors**: Breakdown of the factors that influenced your assessment
5. **Quality Requirements**: Specific guidance on the types and quality of sources needed

Focus on providing actionable, context-specific guidance that balances research thoroughness with implementation efficiency.

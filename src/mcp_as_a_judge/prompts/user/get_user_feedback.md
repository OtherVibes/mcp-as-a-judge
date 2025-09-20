# User Requirements Feedback

## Current Understanding
{{ current_request }}

## Repository Analysis
{{ repository_analysis }}

## Identified Requirement Gaps
{% for gap in identified_gaps %}
- {{ gap }}
{% endfor %}

## Specific Questions for Clarification
{% for question in specific_questions %}
- {{ question }}
{% endfor %}

## Technical Decisions Needed
{% for area in decision_areas %}
- **{{ area }}**: Please specify your preference
{% endfor %}

## Suggested Options with Analysis
{% for option in suggested_options %}
### {{ option.area }}
{% for choice in option.options %}
- **{{ choice.name }}**
  - Pros: {{ choice.pros | join(", ") }}
  - Cons: {{ choice.cons | join(", ") }}
{% endfor %}
{% endfor %}

## Task Context
- **Task ID**: {{ task_id }}
- **Current State**: Requirements feedback gathering
- **Next Step**: Create implementation plan based on your responses

## Instructions

Please provide detailed responses to help create a comprehensive implementation plan:

1. **Answer the specific questions** listed above
2. **Make technical decisions** for the areas identified
3. **Provide any additional context** about constraints, preferences, or requirements
4. **Specify workflow preferences** if you have any (testing approach, deployment preferences, etc.)

Your responses will be used to:
- Update the task requirements with clarified details
- Make informed technical decisions for the implementation
- Create a detailed plan that matches your expectations
- Ensure the implementation follows best practices for your chosen technology stack

The more specific you are, the better the implementation plan will be tailored to your needs.

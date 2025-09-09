Please evaluate the following coding plan:

## User Requirements

{{ user_requirements }}

## Context

{{ context }}

## Previous Conversation History as JSON array 
{{ conversation_history }}

## Plan

{{ plan }}

## Design

{{ design }}

## Research

{{ research|default("") }}

{% if research_required %}
## 🔍 External Research Analysis

**Status:** REQUIRED (Scope: {{ research_scope }})
**Rationale:** {{ research_rationale }}

{% if research_urls %}
**Research Sources:**
{% for url in research_urls %}
- {{ url }}
{% endfor %}

**Validation Focus:** Ensure research demonstrates problem domain authority and established best practices.
{% else %}
⚠️ **MISSING:** External research is required but no URLs provided.
{% endif %}
{% endif %}

{% if internal_research_required %}
## 🏗️ Internal Codebase Analysis

**Status:** REQUIRED - Task should leverage existing patterns.

{% if related_code_snippets %}
**Related Components:**
{% for snippet in related_code_snippets %}
- `{{ snippet }}`
{% endfor %}

**Validation Focus:** Ensure plan follows established patterns and reuses existing components.
{% else %}
⚠️ **MISSING:** Internal analysis required but no code components identified.
{% endif %}
{% endif %}

{% if risk_assessment_required %}
## ⚠️ Risk Assessment

**Status:** REQUIRED - Change has potential to impact existing functionality.

{% if identified_risks %}
**Risk Areas:**
{% for risk in identified_risks %}
- {{ risk }}
{% endfor %}
{% endif %}

{% if risk_mitigation_strategies %}
**Mitigation Strategies:**
{% for strategy in risk_mitigation_strategies %}
- {{ strategy }}
{% endfor %}
{% endif %}

**Validation Focus:** Ensure plan addresses risks with safeguards and rollback mechanisms.
{% endif %}

## Analysis Instructions

As part of your evaluation, you must analyze the task requirements and update the task metadata with conditional requirements:

1. **External Research Analysis**: Determine if external research is needed based on task complexity, specialized domains, or technologies
2. **Internal Codebase Analysis**: Determine if understanding existing codebase patterns is needed
3. **Risk Assessment**: Determine if the task poses risks to existing functionality or system stability

Update the `current_task_metadata` in your response with your analysis of these conditional requirements.

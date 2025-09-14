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

## Problem Domain Statement

{{ problem_domain or "" }}

{% if problem_non_goals %}
### Non-Goals
{% for item in problem_non_goals %}- {{ item }}
{% endfor %}
{% endif %}

{% if library_plan %}
## Library Selection Map (Purpose → Selection)

```
{{ library_plan }}
```
{% endif %}

{% if internal_reuse_components %}
## Internal Reuse Map (Repo Components)

```
{{ internal_reuse_components }}
```
{% endif %}

## Research

{{ research|default("") }}

{% if research_required %}
## 🔍 External Research Analysis

**Status:** REQUIRED (Scope: {{ research_scope }})
**Rationale:** {{ research_rationale }}

{% if expected_url_count > 0 %}
### 🧠 Dynamic URL Requirements (LLM Analysis)
**Expected URLs:** {{ expected_url_count }}
**Minimum URLs:** {{ minimum_url_count }}
**Reasoning:** {{ url_requirement_reasoning }}
{% endif %}

{% if research_urls %}
**Research Sources Provided ({{ research_urls|length }} URLs):**
{% for url in research_urls %}
- {{ url }}
{% endfor %}

**Validation Focus:** 
- Ensure research demonstrates problem domain authority and established best practices
{% if expected_url_count > 0 %}
- Verify {{ research_urls|length }} URLs {% if research_urls|length >= expected_url_count %}meet{% else %}fall short of{% endif %} the expected {{ expected_url_count }} URLs for optimal coverage
- Minimum {{ minimum_url_count }} URLs required for basic adequacy
{% endif %}
{% else %}
⚠️ **MISSING:** External research is required but no URLs provided.
{% if expected_url_count > 0 %}
**Required:** At least {{ minimum_url_count }} URLs ({{ expected_url_count }} recommended)
**Reason:** {{ url_requirement_reasoning }}
{% endif %}
{% endif %}
{% endif %}

{% if internal_research_required %}
## 🏗️ Internal Codebase Analysis

**Status:** REQUIRED - Task should leverage existing patterns when available.

{% if related_code_snippets %}
**Related Components:**
{% for snippet in related_code_snippets %}
- `{{ snippet }}`
{% endfor %}

**Validation Focus:** Ensure plan follows established patterns and reuses existing components.
{% else %}
Note: Internal analysis is marked required but no repository-local components were identified in the provided context. Do not block solely on this. If you cannot identify concrete related components in this repository, set `internal_research_required=false` in current_task_metadata and include a brief note explaining the absence; otherwise, list the specific components.
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

1. **External Research Analysis**: Determine if external research is needed based on task complexity, specialized domains, or technologies. Ensure research coverage maps to ALL major aspects implied by the user requirements (each named framework, protocol, pattern, integration, system), not just a subset.
2. **Internal Codebase Analysis**: Determine if understanding existing codebase patterns is needed
3. **Risk Assessment**: Determine if the task poses risks to existing functionality or system stability

Update the `current_task_metadata` in your response with your analysis of these conditional requirements.

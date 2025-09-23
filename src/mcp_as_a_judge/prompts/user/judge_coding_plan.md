{% macro render_text_section(title, value, empty_message) -%}
## {{ title }}

{% if value is string and value.strip() %}
{{ value }}
{% elif value %}
{{ value }}
{% else %}
⚠️ {{ empty_message }}
{% endif %}
{%- endmacro %}

{% macro render_list_section(title, items, empty_message) -%}
## {{ title }}

{% if items and items | length > 0 %}
{% for item in items %}- {{ item }}
{% endfor %}
{% else %}
- {{ empty_message }}
{% endif %}
{%- endmacro %}

{% macro render_json_section(title, obj, empty_message) -%}
{% set data = obj if obj is not none else [] %}
## {{ title }}

```
{{ data | tojson(indent=2) }}
```

{% if data | length == 0 %}
_Note: {{ empty_message }}_
{% endif %}
{%- endmacro %}

{% macro render_status_block(title, required, scope=None, rationale=None) -%}
## {{ title }}

**Status:** {{ "REQUIRED" if required else "Optional" }}{% if scope %} (Scope: {{ scope }}){% endif %}
{% if rationale %}
**Rationale:** {{ rationale }}
{% endif %}
{%- endmacro %}

Please evaluate the following coding plan:

{{ render_text_section("User Requirements", user_requirements, "User requirements not supplied") }}

{{ render_text_section("Context", context, "Context not provided") }}

## Previous Conversation History as JSON array
```
{{ conversation_history | tojson(indent=2) }}
```

{{ render_text_section("Plan", plan, "Plan input was empty or whitespace only") }}

{{ render_text_section("Design", design, "Design input was empty or whitespace only") }}

{{ render_text_section("Problem Domain Statement", problem_domain or "", "Problem domain missing") }}

{{ render_list_section("Non-Goals", problem_non_goals, "None provided; array submitted as []") }}

{{ render_json_section("Library Selection Map (Purpose → Selection)", library_plan, "Provide a library selection map with purpose, selection, source, and justification") }}

{{ render_json_section("Internal Reuse Map (Repo Components)", internal_reuse_components, "Provide [] with note 'greenfield project - no existing components to reuse' if nothing exists") }}

{{ render_text_section("Research", research, "Research input was empty or whitespace only") }}

{{ render_json_section("Research URLs", research_urls, "Supply research URLs when research_required=true") }}

{% if research_required %}
{{ render_status_block("🔍 External Research Analysis", True, research_scope, research_rationale) }}

{% if expected_url_count and expected_url_count > 0 %}
### 🧠 Dynamic URL Requirements (LLM Analysis)
- **Expected URLs:** {{ expected_url_count }}
- **Minimum URLs:** {{ minimum_url_count }}
- **Reasoning:** {{ url_requirement_reasoning }}
{% endif %}

{% if research_urls and research_urls | length > 0 %}
**Research Sources Provided ({{ research_urls | length }} URLs):**
{% for url in research_urls %}- {{ url }}
{% endfor %}

**Validation Focus:**
- Ensure research demonstrates problem domain authority and established best practices
{% if expected_url_count and expected_url_count > 0 %}
- Verify {{ research_urls | length }} URLs {% if research_urls | length >= expected_url_count %}meet{% else %}fall short of{% endif %} the expected {{ expected_url_count }} URLs for optimal coverage
- Minimum {{ minimum_url_count }} URLs required for basic adequacy
{% endif %}
{% else %}
⚠️ **MISSING:** External research is required but no URLs provided.
{% if expected_url_count and expected_url_count > 0 %}
**Required:** At least {{ minimum_url_count }} URLs ({{ expected_url_count }} recommended)
**Reason:** {{ url_requirement_reasoning }}
{% endif %}
{% endif %}
{% endif %}

{% if internal_research_required %}
{{ render_status_block("🏗️ Internal Codebase Analysis", True) }}

{% if related_code_snippets %}
**Related Components:**
{% for snippet in related_code_snippets %}- `{{ snippet }}`
{% endfor %}

**Validation Focus:** Ensure plan follows established patterns and reuses existing components.
{% else %}
Note: Internal analysis is marked required but no repository-local components were identified in the provided context. Do not block solely on this. If you cannot identify concrete related components in this repository, set `internal_research_required=false` in current_task_metadata and include a brief note explaining the absence; otherwise, list the specific components.
{% endif %}
{% endif %}

{% if risk_assessment_required %}
{{ render_status_block("⚠️ Risk Assessment", True) }}

{{ render_json_section("Identified Risks", identified_risks, "Populate risk array with domain-specific items") }}

{{ render_json_section("Risk Mitigation Strategies", risk_mitigation_strategies, "Provide mitigation entries aligned one-to-one with identified risks") }}

**Validation Focus:** Ensure plan addresses risks with safeguards and rollback mechanisms.
{% endif %}

{% if design_patterns %}
{{ render_json_section("Design Patterns Inventory", design_patterns, "List design pattern objects with name and area") }}
{% endif %}

## Analysis Instructions

As part of your evaluation, you must analyze the task requirements and update the task metadata with conditional requirements:

1. **External Research Analysis**: Determine if external research is needed based on task complexity, specialized domains, or technologies. Ensure research coverage maps to ALL major aspects implied by the user requirements (each named framework, protocol, pattern, integration, system), not just a subset.
2. **Internal Codebase Analysis**: Determine if understanding existing codebase patterns is needed
3. **Risk Assessment**: Determine if the task poses risks to existing functionality or system stability

Update the `current_task_metadata` in your response with your analysis of these conditional requirements.

Please evaluate the following coding plan:

## User Requirements

{{ user_requirements }}

## Context

{{ context }}

## Plan

{{ plan }}

## Design

{{ design }}

## Research

**Research must be based on: Current Repository + User Requirements + MANDATORY Online Investigation**

{{ research }}

## Research URLs

{% if research_urls %}
The following URLs were visited during MANDATORY online research:

{% for url in research_urls %}
- {{ url }}
{% endfor %}

URLs should demonstrate:
- Current repository analysis
- Investigation of existing solutions (current repo capabilities, well-known libraries)
- Preference for existing solutions over in-house development
{% else %}
🚨 **CRITICAL: NO RESEARCH URLS PROVIDED** - Online research is MANDATORY.
AI assistant MUST perform online research and provide URLs demonstrating:
- Current repository analysis
- Investigation of existing solutions (current repo capabilities, well-known libraries)
- Preference for existing solutions over in-house development

**This submission should be REJECTED for lack of required online research.**
{% endif %}

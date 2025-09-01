Please validate the research quality for this development task:

## User Requirements

{{ user_requirements }}

## Plan

{{ plan }}

## Design

{{ design }}

## Research Provided

**Expected Research Foundation: Current Repository + User Requirements + MANDATORY Online Investigation**

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
- Prioritization of existing solutions over in-house development
{% else %}
🚨 **CRITICAL: NO RESEARCH URLS PROVIDED** - Online research is MANDATORY.
This indicates no online research was performed, which should result in REJECTION.
Research MUST include URLs demonstrating:
- Current repository analysis
- Investigation of existing solutions (current repo capabilities, well-known libraries)
- Prioritization of existing solutions over in-house development
{% endif %}

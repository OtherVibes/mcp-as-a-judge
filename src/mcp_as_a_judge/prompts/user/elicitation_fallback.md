🤖 **ELICITATION NOT AVAILABLE - PLEASE ASK USER DIRECTLY**

{{ original_message }}

**Please ask the user to provide the following information:**

{% if required_fields %}
**Required Information:**
{% for field in required_fields %}
{{ field }}
{% endfor %}

{% endif %}
{% if optional_fields %}
**Optional Information:**
{% for field in optional_fields %}
{{ field }}
{% endfor %}

{% endif %}
**Instructions for AI Assistant:**
1. Ask the user for each piece of information listed above
2. Present the questions in a clear, conversational manner
3. Collect the user's responses
4. Once you have the information, proceed with the task using the user's input

**Note:** This fallback occurred because MCP elicitation is not available in your environment. Please manually collect this information from the user.

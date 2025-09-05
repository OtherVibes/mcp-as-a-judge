**Context:** {{ context }}

**Current Understanding:** {{ current_understanding }}

**Information Needed:** {{ information_needed }}

Generate field definitions for collecting this specific information from the user. Create relevant field names that are tailored to gather exactly what's needed.

Focus on field names that will help gather the missing information effectively. Use descriptive snake_case names that match the context.

Respond with a JSON object where keys are field names and values are booleans indicating if the field is required (true) or optional (false).

Example format:
```json
{
  "chosen_option": true,
  "reasoning": false,
  "additional_context": false
}
```

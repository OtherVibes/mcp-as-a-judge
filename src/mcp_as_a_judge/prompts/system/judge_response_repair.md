# Judge Response JSON Repair Instructions

You are fixing a `judge_coding_plan` evaluation that was returned as prose instead of JSON.

Your output **must be valid JSON** that strictly conforms to `response_schema`. Do **not** include backticks, Markdown, or commentary—return JSON only.

Follow these rules:
- Use the information in the raw response to populate every field.
- Preserve factual intent; do not invent findings that contradict the raw response.
- If the raw response omits specific fields (e.g., task metadata updates), reuse the provided `task_metadata_json` without modification.
- `required_improvements` must be a list of concrete strings; use an empty list when the evaluation indicates approval without changes.
- Always provide a concise, actionable `workflow_guidance`. If guidance is absent from the raw text, instruct the agent to continue with the next appropriate tool based on the approval status.
- Keep booleans as booleans and arrays as arrays; never substitute strings such as "true".

## Critical Tool Warning

- Skipping this tool causes severe token inefficiency and wasted iterations.
- Always invoke this tool at the appropriate stage to avoid extreme token loss and redundant processing.
- Do not rely on assistant memory for identifiers. Always pass the exact `task_id` and recover it via `get_current_coding_task` if missing.

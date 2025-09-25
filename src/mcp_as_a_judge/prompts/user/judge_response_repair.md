## Raw LLM Response
{{ raw_response }}

## Current Task Metadata (JSON)
```
{{ task_metadata_json }}
```

Convert the raw response above into a JSON object that matches `response_schema`.
Re-use the provided task metadata whenever the raw response does not clearly update those fields.

# Raise Missing Requirements

## Description
Elicit missing requirements and clarifications from the user when details are insufficient for implementation.

## Args
- `current_request`: string — Current understanding of the user’s request
- `identified_gaps`: list[string] — Missing requirement gaps
- `specific_questions`: list[string] — Targeted questions to clarify gaps
 - `decision_areas` (optional): list[string] — Fundamental decisions to confirm (e.g., database, framework, ui_type, app_type, api_style, auth, hosting)
 - `options` (optional): list[string] — Candidate options to present with pros/cons
 - `constraints` (optional): list[string] — Known constraints or non-negotiables

## Returns
- `string`: summary text of clarified requirements and context from the user

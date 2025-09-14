# Raise Obstacle

## Description
Involve the user to resolve blockers or conflicts by presenting options and context.

## Args
- `problem`: string — Clear description of the obstacle
- `research`: string — What has been investigated (alternatives, prior art)
- `options`: list[string] — Possible approaches or next steps
 - `decision_area` (optional): string — Name of the decision area involved (e.g., database, framework)
 - `constraints` (optional): list[string] — Known constraints or non-negotiables

## Returns
- `string`: user's decision and any additional context for proceeding

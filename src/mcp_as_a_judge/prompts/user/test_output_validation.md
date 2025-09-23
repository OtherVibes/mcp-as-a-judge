# Test Output Validation Request

Please analyze the following text to determine if it represents authentic test execution output.

## Test Output to Analyze

```
{{ test_output }}
```

## Context

{{ context }}

## Analysis Required

Please evaluate:

1. **Framework Detection**: What test framework (if any) produced this output?
2. **Authenticity**: Does this look like genuine test runner output?
3. **Completeness**: Does it contain the expected elements of test execution?
4. **Quality**: Is this sufficient evidence of test execution?

## Response Requirements

Provide a JSON response with:
- `looks_like_test_output`: Boolean indicating if this appears to be genuine test output
- `test_framework_detected`: The specific test framework identified
- `has_test_results`: Whether actual test results are present
- `has_execution_summary`: Whether a test execution summary is included
- `confidence_score`: Your confidence level (0.0 to 1.0)
- `issues`: List any specific problems with the output
- `feedback`: Detailed explanation of your assessment

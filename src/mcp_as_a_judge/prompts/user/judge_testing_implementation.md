# Testing Implementation Evaluation Request

Please evaluate the testing implementation for the following coding task:

## Task Context

**User Requirements:**
{{ user_requirements }}

**Task Description:**
{{ task_description }}

**Implementation Files Modified:**
{% for file in modified_files %}
- {{ file }}
{% endfor %}

## Testing Implementation Details

**Test Summary:**
{{ test_summary }}

**Test Files Created:**
{% for test_file in test_files %}
- {{ test_file }}
{% endfor %}

**Test Execution Results:**
```
{{ test_execution_results }}
```

**Test Coverage Report:**
```
{{ test_coverage_report }}
```

**Test Types Implemented:**
{% for test_type in test_types_implemented %}
- {{ test_type }}
{% endfor %}

**Testing Framework:**
{{ testing_framework }}

**Performance Test Results:**
```
{{ performance_test_results }}
```

**Manual Test Notes:**
```
{{ manual_test_notes }}
```

## Conversation History Context

{% for entry in conversation_history %}
**{{ entry.timestamp }}** - {{ entry.tool }}:
Input: {{ entry.input }}
Output: {{ entry.output }}

---
{% endfor %}

## Evaluation Requirements

Please provide a comprehensive evaluation focusing on:

### 1. Test Coverage Assessment
- Do the tests adequately cover all implemented functionality?
- Are all user requirements validated through tests?
- Are edge cases and error conditions properly tested?
- Is the test coverage percentage adequate?

### 2. Test Quality Analysis
- Are the tests well-structured and readable?
- Do they follow best practices for the testing framework?
- Are test names descriptive and clear?
- Are tests independent and properly isolated?

### 3. Test Execution Validation
- Do all tests pass without failures or errors?
- Are there any warnings that need to be addressed?
- Do tests run efficiently without performance issues?
- Are the tests reliable and deterministic?

### 4. Test Type Appropriateness
- Are the right types of tests implemented (unit, integration, e2e)?
- Is there an appropriate balance of test types?
- Are integration points properly tested?
- Are end-to-end workflows validated?

### 5. Requirements Compliance
- Do the tests validate that all user requirements are met?
- Are business logic scenarios properly covered?
- Are security aspects tested (if applicable)?
- Are performance characteristics validated (if applicable)?

### 6. Framework and Best Practices
- Do tests follow established patterns for the testing framework?
- Are testing conventions and standards followed?
- Is test organization logical and maintainable?
- Are test utilities and helpers used appropriately?

## Critical Evaluation Points

**APPROVE** the testing implementation if:
- ✅ All tests pass without failures or concerning warnings
- ✅ Test coverage is comprehensive for all implemented functionality
- ✅ Tests are well-written, readable, and maintainable
- ✅ Edge cases and error conditions are properly tested
- ✅ Appropriate mix of test types for the functionality
- ✅ Tests follow framework best practices and conventions
- ✅ All user requirements are validated through tests

**REJECT** the testing implementation if:
- ❌ Any tests fail or produce errors
- ❌ Test coverage is inadequate for key functionality
- ❌ Tests are poorly written or unmaintainable
- ❌ Critical edge cases or error conditions are missing
- ❌ Test execution produces warnings that need attention
- ❌ Inappropriate testing approach for the functionality
- ❌ Tests don't follow established framework patterns

## Response Instructions

Provide your evaluation as a JSON response with:
- `approved`: boolean indicating if testing implementation is approved
- `required_improvements`: array of specific improvements needed (if not approved)
- `feedback`: detailed explanation of your evaluation, including specific observations about test quality, coverage, and compliance with requirements

Focus on ensuring the testing implementation truly validates the functionality and meets professional quality standards.

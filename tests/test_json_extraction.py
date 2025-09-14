#!/usr/bin/env python3
"""Test the JSON extraction functionality for LLM responses."""

import json

import pytest

from mcp_as_a_judge.core.server_helpers import extract_json_from_response
from mcp_as_a_judge.models import (
    JudgeResponse,
    ResearchValidationResponse,
    WorkflowGuidance,
)


class TestJsonExtraction:
    """Test the extract_json_from_response function with various input formats."""

    def test_markdown_wrapped_json(self):
        """Test extraction from markdown code blocks (the original problem case)."""
        test_response = """```json
{
    "research_adequate": true,
    "design_based_on_research": true,
    "issues": [],
    "feedback": "The research provided is comprehensive and well-aligned with the user requirements."
}
```"""

        extracted = extract_json_from_response(test_response)

        # Should extract clean JSON
        expected = """{
    "research_adequate": true,
    "design_based_on_research": true,
    "issues": [],
    "feedback": "The research provided is comprehensive and well-aligned with the user requirements."
}"""
        assert extracted == expected

        # Should be valid JSON
        parsed = json.loads(extracted)
        assert parsed["research_adequate"] is True
        assert parsed["design_based_on_research"] is True
        assert parsed["issues"] == []

    def test_plain_json(self):
        """Test extraction from plain JSON without markdown."""
        test_response = """{"approved": false, "required_improvements": ["Add tests"], "feedback": "Needs work"}"""

        extracted = extract_json_from_response(test_response)

        # Should return the same JSON
        assert extracted == test_response

        # Should be valid JSON
        parsed = json.loads(extracted)
        assert parsed["approved"] is False
        assert "Add tests" in parsed["required_improvements"]

    def test_json_with_surrounding_text(self):
        """Test extraction from JSON with explanatory text before and after."""
        test_response = """Here is the evaluation result:

{
    "approved": true,
    "required_improvements": [],
    "feedback": "Excellent work on this implementation"
}

That concludes the analysis. Please proceed with implementation."""

        extracted = extract_json_from_response(test_response)

        expected = """{
    "approved": true,
    "required_improvements": [],
    "feedback": "Excellent work on this implementation"
}"""
        assert extracted == expected

        # Should be valid JSON
        parsed = json.loads(extracted)
        assert parsed["approved"] is True
        assert parsed["required_improvements"] == []

    def test_nested_json_objects(self):
        """Test extraction from JSON with nested objects."""
        test_response = """```json
{
    "next_tool": "judge_coding_plan",
    "reasoning": "Need to validate the plan",
    "preparation_needed": ["Create plan", "Design system"],
    "guidance": "Start with planning workflow"
}
```"""

        extracted = extract_json_from_response(test_response)

        # Should be valid JSON
        parsed = json.loads(extracted)
        assert parsed["next_tool"] == "judge_coding_plan"
        assert len(parsed["preparation_needed"]) == 2

    def test_no_json_found(self):
        """Test error handling when no JSON object is found."""
        test_response = """This is just plain text without any JSON object in it."""

        with pytest.raises(ValueError, match="No valid JSON object found in response"):
            extract_json_from_response(test_response)

    def test_malformed_braces(self):
        """Test error handling when braces are malformed."""
        # Test case with no closing brace
        test_response_no_close = """{ this is not valid JSON but has braces"""

        with pytest.raises(ValueError, match="No valid JSON object found in response"):
            extract_json_from_response(test_response_no_close)

        # Test case with valid braces but invalid JSON content
        test_response_invalid_json = (
            """{ this is not valid JSON but has closing brace }"""
        )

        extracted = extract_json_from_response(test_response_invalid_json)
        assert extracted == "{ this is not valid JSON but has closing brace }"

        # But it should fail when trying to parse as JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(extracted)

    def test_multiple_json_objects(self):
        """Test that it extracts from first { to last } when multiple objects exist."""
        test_response = """First object: {"a": 1} and second object: {"b": 2}"""

        extracted = extract_json_from_response(test_response)

        # Should extract from first { to last }
        assert extracted == """{"a": 1} and second object: {"b": 2}"""

    def test_with_pydantic_models(self):
        """Test that extracted JSON works with Pydantic model validation."""
        # Test ResearchValidationResponse
        research_response = """```json
{
    "research_adequate": true,
    "design_based_on_research": false,
    "issues": ["Design not based on research"],
    "feedback": "Research is good but design needs alignment"
}
```"""

        extracted = extract_json_from_response(research_response)
        model = ResearchValidationResponse.model_validate_json(extracted)

        assert model.research_adequate is True
        assert model.design_based_on_research is False
        assert "Design not based on research" in model.issues
        assert "alignment" in model.feedback

        # Test JudgeResponse
        judge_response = """```json
{
    "approved": false,
    "required_improvements": ["Add error handling", "Improve documentation"],
    "feedback": "Code needs improvements before approval"
}
```"""

        extracted = extract_json_from_response(judge_response)
        model = JudgeResponse.model_validate_json(extracted)

        assert model.approved is False
        assert len(model.required_improvements) == 2
        assert "error handling" in model.required_improvements[0]

        # Test WorkflowGuidance
        workflow_response = """```json
{
    "next_tool": "judge_code_change",
    "reasoning": "Code has been written and needs review",
    "preparation_needed": ["Gather code changes", "Document requirements"],
    "guidance": "Call judge_code_change with the written code"
}
```"""

        extracted = extract_json_from_response(workflow_response)
        model = WorkflowGuidance.model_validate_json(extracted)

        assert model.next_tool == "judge_code_change"
        assert "review" in model.reasoning
        assert len(model.preparation_needed) == 2

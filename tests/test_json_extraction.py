#!/usr/bin/env python3
"""Test the JSON extraction functionality for LLM responses."""

import json
import sys
from types import ModuleType, SimpleNamespace

import pytest
from pydantic import BaseModel, Field

if "litellm" not in sys.modules:
    sys.modules["litellm"] = SimpleNamespace(
        RateLimitError=RuntimeError,
        completion=lambda **kwargs: {},
        drop_params=False,
        suppress_debug_info=False,
        set_verbose=False,
    )

if "tenacity" not in sys.modules:

    def _retry_stub(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    sys.modules["tenacity"] = SimpleNamespace(
        retry=_retry_stub,
        retry_if_exception_type=lambda *args, **kwargs: None,
        stop_after_attempt=lambda *args, **kwargs: None,
        wait_exponential=lambda *args, **kwargs: None,
    )

if "mcp_as_a_judge.workflow" not in sys.modules:
    workflow_module = ModuleType("mcp_as_a_judge.workflow")
    workflow_guidance_module = ModuleType("mcp_as_a_judge.workflow.workflow_guidance")

    class WorkflowGuidance(BaseModel):
        next_tool: str | None = None
        reasoning: str = ""
        preparation_needed: list[str] = Field(default_factory=list)
        guidance: str = ""
        research_required: bool | None = None
        research_scope: str | None = None
        research_rationale: str | None = None
        internal_research_required: bool | None = None
        risk_assessment_required: bool | None = None
        design_patterns_enforcement: bool | None = None
        plan_required_fields: list[dict] = Field(default_factory=list)

    def _generate_plan_required_fields(*_, **__):
        return []

    def calculate_next_stage(*_, **__):
        return WorkflowGuidance()

    workflow_guidance_module.WorkflowGuidance = WorkflowGuidance
    workflow_guidance_module._generate_plan_required_fields = (
        _generate_plan_required_fields
    )
    workflow_module.WorkflowGuidance = WorkflowGuidance
    workflow_module.calculate_next_stage = calculate_next_stage
    workflow_module._generate_plan_required_fields = _generate_plan_required_fields
    workflow_module.workflow_guidance = workflow_guidance_module

    sys.modules["mcp_as_a_judge.workflow"] = workflow_module
    sys.modules["mcp_as_a_judge.workflow.workflow_guidance"] = workflow_guidance_module

from mcp_as_a_judge.core.server_helpers import (
    _coerce_markdown_judge_response,
    extract_json_from_response,
)
from mcp_as_a_judge.models import JudgeResponse, ResearchValidationResponse
from mcp_as_a_judge.models.enhanced_responses import (
    rebuild_models as rebuild_enhanced_models,
)
from mcp_as_a_judge.models.task_metadata import TaskMetadata, TaskSize

rebuild_enhanced_models()


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

        # Test parsing with a generic pydantic model
        workflow_response = """```json
{
    "next_tool": "judge_code_change",
    "reasoning": "Code has been written and needs review",
    "preparation_needed": ["Gather code changes", "Document requirements"],
    "guidance": "Call judge_code_change with the written code"
}
```"""

        class DummyGuidance(BaseModel):
            next_tool: str | None
            reasoning: str
            preparation_needed: list[str]
            guidance: str

        extracted = extract_json_from_response(workflow_response)
        model = DummyGuidance.model_validate_json(extracted)

        assert model.next_tool == "judge_code_change"
        assert "review" in model.reasoning
        assert len(model.preparation_needed) == 2


class TestMarkdownJudgeResponseCoercion:
    """Tests for deterministic markdown-to-JSON coercion fallback."""

    def _build_task_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            title="Sample Task",
            description="Ensure fallback works",
            task_size=TaskSize.M,
        )

    def test_reject_response_with_required_corrections(self):
        """Markdown rejection response should produce structured JudgeResponse."""

        raw_response = (
            "**Decision:** ❌ Reject\n\n"
            "**Reasons (per explicit workflow guidance only):**\n"
            "1. Fallback behavior insufficiently specified.\n"
            "2. Output schema not concretely enumerated.\n\n"
            "**Required Corrections:**\n"
            "- Add a concise explicit output schema (field names, types, example).\n"
            "- Specify precise logic per method: how you detect presence and authenticated state.\n"
            "- Define exact fallback outputs for:\n"
            "  a) No method configured\n"
            "  b) Multiple methods present but none active\n"
            "  c) Unknown/legacy or partial credentials\n"
            "- Clarify whether /auth with no args opens dialog (current plan) and confirm how a user sees status without remembering subcommand (consider brief rationale this is acceptable).\n"
        )

        task_metadata = self._build_task_metadata()
        result = _coerce_markdown_judge_response(raw_response, task_metadata)

        assert result is not None
        assert result.approved is False
        assert result.current_task_metadata is task_metadata
        assert any(
            "explicit output schema" in improvement.lower()
            for improvement in result.required_improvements
        )
        assert len(result.required_improvements) >= 4
        assert result.feedback.startswith("**Decision:** ❌ Reject")
        assert (
            result.workflow_guidance.preparation_needed == result.required_improvements
        )
        assert "plan rejected" in result.workflow_guidance.reasoning.lower()

    def test_approval_response_returns_empty_improvements(self):
        """Approved markdown response should keep improvements empty."""

        raw_response = (
            "**Decision:** ✅ Approve\n\n"
            "**Summary:** Plan meets all workflow requirements.\n"
        )

        task_metadata = self._build_task_metadata()
        result = _coerce_markdown_judge_response(raw_response, task_metadata)

        assert result is not None
        assert result.approved is True
        assert result.required_improvements == []
        assert result.workflow_guidance.preparation_needed == []
        assert "approved" in result.workflow_guidance.reasoning.lower()

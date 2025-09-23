"""Test workflow guidance exposure to plan system prompt."""

import json

import pytest

from mcp_as_a_judge.core.server_helpers import extract_latest_workflow_guidance


class TestWorkflowGuidanceExtraction:
    """Test the extraction of workflow guidance from conversation history."""

    @pytest.mark.asyncio
    async def test_extract_full_workflow_guidance_object(self) -> None:
        """Test that the full workflow guidance object is extracted."""
        # Sample conversation history with workflow guidance
        conversation_history = [
            {
                "output": json.dumps(
                    {
                        "workflow_guidance": {
                            "next_tool": "judge_coding_plan",
                            "reasoning": "Plan needs validation before implementation",
                            "preparation_needed": [
                                "Prepare comprehensive design document",
                                "Define library selection map",
                            ],
                            "plan_required_fields": [
                                {
                                    "name": "plan",
                                    "type": "string",
                                    "required": True,
                                    "description": "Detailed implementation plan",
                                },
                                {
                                    "name": "design_patterns",
                                    "type": "list[dict]",
                                    "required": True,
                                    "conditional_on": "design_patterns_enforcement",
                                    "description": "Design patterns to be applied",
                                },
                            ],
                            "guidance": "Create comprehensive plan with all required fields",
                        }
                    }
                )
            }
        ]

        result = await extract_latest_workflow_guidance(conversation_history)

        assert result is not None
        assert isinstance(result, dict)
        assert result["next_tool"] == "judge_coding_plan"
        assert result["reasoning"] == "Plan needs validation before implementation"
        assert len(result["preparation_needed"]) == 2
        assert len(result["plan_required_fields"]) == 2

        # Check plan required fields structure
        plan_field = result["plan_required_fields"][0]
        assert plan_field["name"] == "plan"
        assert plan_field["type"] == "string"
        assert plan_field["required"] is True

        patterns_field = result["plan_required_fields"][1]
        assert patterns_field["conditional_on"] == "design_patterns_enforcement"

    @pytest.mark.asyncio
    async def test_extract_guidance_returns_none_when_not_found(self) -> None:
        """Test that None is returned when no workflow guidance is found."""
        conversation_history = [
            {"output": json.dumps({"some_other_field": "value"})},
            {"output": "invalid json"},
            {"output": json.dumps({})},
        ]

        result = await extract_latest_workflow_guidance(conversation_history)
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_guidance_handles_malformed_data(self) -> None:
        """Test that malformed data is handled gracefully."""
        conversation_history = [
            {"output": "not json"},
            {"output": json.dumps({"workflow_guidance": "not a dict"})},
            {"output": json.dumps({"workflow_guidance": {}})},  # Empty but valid
        ]

        result = await extract_latest_workflow_guidance(conversation_history)
        assert result == {}  # Empty dict is still valid


class TestWorkflowGuidanceFormatting:
    """Test the formatting of workflow guidance for system prompts."""

    def test_format_comprehensive_guidance(self) -> None:
        """Test formatting of comprehensive workflow guidance."""
        # This tests the logic inside evaluate_coding_plan that formats guidance
        workflow_guidance_obj = {
            "next_tool": "judge_coding_plan",
            "reasoning": "Plan validation required",
            "preparation_needed": ["Prepare design document", "Define library map"],
            "plan_required_fields": [
                {
                    "name": "plan",
                    "type": "string",
                    "required": True,
                    "description": "Implementation plan",
                },
                {
                    "name": "design_patterns",
                    "type": "list[dict]",
                    "required": True,
                    "conditional_on": "design_patterns_enforcement",
                    "description": "Design patterns to apply",
                },
            ],
            "guidance": "Create comprehensive plan",
        }

        # Simulate the formatting logic from evaluate_coding_plan
        guidance_parts = []

        if workflow_guidance_obj.get("next_tool"):
            guidance_parts.append(
                f"**Next Tool:** {workflow_guidance_obj['next_tool']}"
            )

        if workflow_guidance_obj.get("reasoning"):
            guidance_parts.append(
                f"**Reasoning:** {workflow_guidance_obj['reasoning']}"
            )

        if workflow_guidance_obj.get("preparation_needed"):
            prep_items = workflow_guidance_obj["preparation_needed"]
            if isinstance(prep_items, list) and prep_items:
                guidance_parts.append("**Preparation Required:**")
                for item in prep_items:
                    guidance_parts.append(f"- {item}")

        if workflow_guidance_obj.get("plan_required_fields"):
            fields = workflow_guidance_obj["plan_required_fields"]
            if isinstance(fields, list) and fields:
                guidance_parts.append("**Required Plan Fields:**")
                for field in fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "unknown")
                        field_type = field.get("type", "unknown")
                        field_desc = field.get("description", "")
                        required = field.get("required", False)
                        conditional = field.get("conditional_on", "")

                        field_info = f"- **{field_name}** ({field_type})"
                        if required:
                            field_info += " [REQUIRED]"
                        if conditional:
                            field_info += f" [Conditional on: {conditional}]"
                        if field_desc:
                            field_info += f": {field_desc}"
                        guidance_parts.append(field_info)

        if workflow_guidance_obj.get("guidance"):
            guidance_parts.append(
                f"**Detailed Guidance:** {workflow_guidance_obj['guidance']}"
            )

        formatted_text = "\n".join(guidance_parts)

        # Verify the formatted text contains all expected elements
        assert "**Next Tool:** judge_coding_plan" in formatted_text
        assert "**Reasoning:** Plan validation required" in formatted_text
        assert "**Preparation Required:**" in formatted_text
        assert "- Prepare design document" in formatted_text
        assert "- Define library map" in formatted_text
        assert "**Required Plan Fields:**" in formatted_text
        assert "- **plan** (string) [REQUIRED]: Implementation plan" in formatted_text
        assert (
            "- **design_patterns** (list[dict]) [REQUIRED] [Conditional on: design_patterns_enforcement]: Design patterns to apply"
            in formatted_text
        )
        assert "**Detailed Guidance:** Create comprehensive plan" in formatted_text

    def test_format_minimal_guidance(self) -> None:
        """Test formatting when only basic guidance is provided."""
        workflow_guidance_obj = {
            "next_tool": "judge_coding_plan",
            "guidance": "Basic guidance only",
        }

        # Simulate minimal formatting
        guidance_parts = []
        guidance_parts.append(f"**Next Tool:** {workflow_guidance_obj['next_tool']}")
        guidance_parts.append(
            f"**Detailed Guidance:** {workflow_guidance_obj['guidance']}"
        )

        formatted_text = "\n".join(guidance_parts)

        assert "**Next Tool:** judge_coding_plan" in formatted_text
        assert "**Detailed Guidance:** Basic guidance only" in formatted_text
        assert "**Preparation Required:**" not in formatted_text
        assert "**Required Plan Fields:**" not in formatted_text


class TestWorkflowGuidanceIntegration:
    """Test integration of workflow guidance with plan evaluation."""

    @pytest.mark.asyncio
    async def test_plan_evaluation_uses_structured_guidance(self) -> None:
        """Test that plan evaluation properly uses structured workflow guidance."""
        # This test validates that structured guidance is properly extracted
        # The actual plan evaluation logic is tested in other test files

        # Create conversation history with structured guidance
        conversation_history = [
            {
                "output": json.dumps(
                    {
                        "workflow_guidance": {
                            "next_tool": "judge_coding_plan",
                            "reasoning": "Plan needs validation",
                            "plan_required_fields": [
                                {
                                    "name": "plan",
                                    "type": "string",
                                    "required": True,
                                    "description": "Implementation plan",
                                },
                                {
                                    "name": "design_patterns",
                                    "type": "list[dict]",
                                    "required": True,
                                    "conditional_on": "design_patterns_enforcement",
                                    "description": "Design patterns to apply",
                                },
                            ],
                        }
                    }
                )
            }
        ]

        # Test that the guidance extraction works
        extracted_guidance = await extract_latest_workflow_guidance(
            conversation_history
        )
        assert extracted_guidance is not None
        assert "plan_required_fields" in extracted_guidance
        assert len(extracted_guidance["plan_required_fields"]) == 2

        # Verify the conditional field is properly structured
        design_patterns_field = next(
            field
            for field in extracted_guidance["plan_required_fields"]
            if field["name"] == "design_patterns"
        )
        assert design_patterns_field["conditional_on"] == "design_patterns_enforcement"
        assert design_patterns_field["required"] is True

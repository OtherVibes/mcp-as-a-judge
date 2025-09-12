#!/usr/bin/env python3
"""Test the response models for MCP as a Judge."""

import os
import sys

from mcp_as_a_judge.models import JudgeResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_judge_response_model() -> None:
    """Test that the JudgeResponse model works correctly."""
    print("Testing JudgeResponse model...")

    # Test approved response
    approved_response = JudgeResponse(
        approved=True,
        required_improvements=[],
        feedback="The coding plan follows all best practices.",
    )

    assert approved_response.approved
    assert approved_response.required_improvements == []
    assert "best practices" in approved_response.feedback
    print("✓ Approved response model works")

    # Test needs revision response
    revision_response = JudgeResponse(
        approved=False,
        required_improvements=[
            "Add input validation",
            "Implement proper error handling",
            "Add unit tests",
        ],
        feedback="The code needs several improvements before approval.",
    )

    assert not revision_response.approved
    assert len(revision_response.required_improvements) == 3
    assert "Add input validation" in revision_response.required_improvements
    print("✓ Needs revision response model works")

    # Test JSON serialization
    json_data = approved_response.model_dump(exclude_none=True)
    assert json_data["approved"]
    assert json_data["required_improvements"] == []
    print("✓ JSON serialization works")

    # Test JSON deserialization
    reconstructed = JudgeResponse(**json_data)
    assert reconstructed.approved == approved_response.approved
    assert (
        reconstructed.required_improvements == approved_response.required_improvements
    )
    print("✓ JSON deserialization works")

    print("✓ All model tests passed!")
    assert True  # All checks passed


if __name__ == "__main__":
    success = test_judge_response_model()
    sys.exit(0 if success else 1)

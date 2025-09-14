#!/usr/bin/env python3
"""Test that the judge_coding_plan function properly validates design and research parameters."""

import inspect
import os
import sys

from mcp_as_a_judge.server import judge_coding_plan

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_judge_coding_plan_signature() -> None:
    """Test that judge_coding_plan has the required design and research parameters."""
    print("Testing judge_coding_plan function signature...")

    # Get the function signature
    sig = inspect.signature(judge_coding_plan)
    params = list(sig.parameters.keys())

    # Check that all required parameters are present
    required_params = ["plan", "design", "research", "research_urls"]
    for param in required_params:
        assert param in params, f"Missing required parameter: {param}"
        print(f"✓ Parameter '{param}' is present")

    # Check that design and research are required (no default value)
    assert sig.parameters["plan"].default == inspect.Parameter.empty, (
        "plan should be required"
    )
    assert sig.parameters["design"].default == inspect.Parameter.empty, (
        "design should be required"
    )
    assert sig.parameters["research"].default == inspect.Parameter.empty, (
        "research should be required"
    )
    # research_urls is now required
    assert sig.parameters["research_urls"].default == inspect.Parameter.empty, (
        "research_urls should be required"
    )
    print("✓ plan, design, and research are all required parameters")

    # Check that context is optional
    assert sig.parameters["context"].default == "", "context should have default value"
    print("✓ context is optional with default value")

    # Check return type annotation
    return_annotation = sig.return_annotation
    assert return_annotation.__name__ == "JudgeResponse", (
        f"Expected JudgeResponse return type, got {return_annotation}"
    )
    print("✓ Return type is JudgeResponse")

    print("✓ All signature tests passed!")
    assert True  # All checks passed


def test_function_docstring() -> None:
    """Test that the function docstring is properly loaded from tool description provider."""
    print("Testing function docstring...")

    docstring = judge_coding_plan.__doc__
    assert docstring is not None, "Function should have a docstring"

    # Check that docstring mentions tool description provider (dynamic loading)
    assert "tool_description_provider" in docstring.lower(), (
        "Docstring should mention tool_description_provider"
    )
    assert "coding plan" in docstring.lower(), "Docstring should mention coding plan"
    print("✓ Docstring mentions tool description provider and coding plan")

    # Check that it has the expected content
    assert "evaluation tool" in docstring.lower(), "Should mention evaluation tool"
    print("✓ Docstring content is correct")

    print("✓ All docstring tests passed!")


if __name__ == "__main__":
    success1 = test_judge_coding_plan_signature()
    success2 = test_function_docstring()

    if success1 and success2:
        print("\n✅ All design and research validation tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

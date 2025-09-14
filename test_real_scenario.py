#!/usr/bin/env python3
"""
Test script to verify real scenario behavior.
"""

import asyncio
from unittest.mock import MagicMock

from mcp_as_a_judge.server import raise_missing_requirements


async def test_real_scenario():
    """Test real scenario with no success check."""
    print("Testing real scenario with no success check...")

    # Create a mock context that doesn't support elicitation
    mock_ctx = MagicMock()
    mock_ctx.elicit = MagicMock(side_effect=Exception("Method not found"))

    # Test the raise_missing_requirements function
    result = await raise_missing_requirements(
        current_request="Implement a new API endpoint for user profile updates",
        identified_gaps=[
            "Required fields for profile updates",
            "Validation rules for each field",
            "Authentication requirements",
        ],
        specific_questions=[
            "What fields should be updatable?",
            "Should we validate email format?",
            "Is admin approval required?",
        ],
        ctx=mock_ctx,
    )

    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result)}")
    print(f"Result preview: {result[:200]}...")

    # Check what type of message we get
    if "ELICITATION NOT AVAILABLE" in result:
        print("❌ Still getting fallback message")
    elif "MCP elicitation failed" in result:
        print("✅ Getting MCP failure message directly")
    elif "REQUIREMENTS CLARIFIED" in result:
        print("✅ Getting success message")
    else:
        print("❓ Getting unexpected message type")


async def main():
    """Run the test."""
    await test_real_scenario()


if __name__ == "__main__":
    asyncio.run(main())

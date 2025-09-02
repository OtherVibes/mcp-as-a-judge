#!/usr/bin/env python3
"""Test that the MCP server can start up properly.

This test verifies the server initialization without running it indefinitely.
"""

import asyncio
import os
import sys

from mcp_as_a_judge.server import mcp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def test_server_startup() -> None:
    """Test that the server can be initialized properly."""
    print("Testing MCP server startup...")

    try:
        # Test that the server has the expected name
        assert mcp.name == "MCP as a Judge", (
            f"Expected 'MCP as a Judge', got '{mcp.name}'"
        )
        print(f"✓ Server name is correct: {mcp.name}")

        # Test that the server is a FastMCP instance
        from mcp.server.fastmcp import FastMCP

        assert isinstance(mcp, FastMCP), f"Expected FastMCP instance, got {type(mcp)}"
        print("✓ Server is FastMCP instance")

        print("✓ All startup tests passed!")
        return True

    except Exception as e:
        print(f"✗ Server startup test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_server_startup())
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Entry point for running MCP as a Judge locally.

This allows the package to be executed with:
    python -m mcp_as_a_judge

For development and testing purposes.
"""

import asyncio
from .server import mcp

async def main():
    """Main entry point for the MCP server."""
    print("Starting MCP as a Judge server...")
    print("Use Ctrl+C to stop the server")

    # The FastMCP server can be run directly
    # In a real deployment, this would typically be handled by the MCP client
    print("MCP server initialized with tools:")
    tools = await mcp.list_tools()
    for tool in tools:
        print(f"  - {tool.name}")

    print("\nServer is ready to receive MCP requests.")
    print("Note: This is a development entry point.")
    print("For production, use the Cloudflare Workers deployment.")

if __name__ == "__main__":
    asyncio.run(main())

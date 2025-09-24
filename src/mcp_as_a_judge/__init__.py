"""
MCP as a Judge - A Model Context Protocol server for software engineering validation.

This package provides MCP tools for validating coding plans and code changes
against software engineering best practices.
"""

__version__ = "0.4.0"


# Lazy imports to avoid dependency issues in Cloudflare Workers
def __getattr__(name: str) -> object:
    if name == "JudgeResponse":
        from mcp_as_a_judge.models import JudgeResponse

        return JudgeResponse
    elif name == "mcp":
        from mcp_as_a_judge.server import mcp

        return mcp
    elif name == "main":
        from mcp_as_a_judge.server import main

        return main
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

"""
MCP as a Judge - A Model Context Protocol server for software engineering validation.

This package provides MCP tools for validating coding plans and code changes
against software engineering best practices.
"""

from mcp_as_a_judge.models import JudgeResponse
from mcp_as_a_judge.server import main, mcp

__version__ = "1.0.0"
__all__ = ["JudgeResponse", "main", "mcp"]

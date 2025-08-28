"""
MCP as a Judge - A Model Context Protocol server for software engineering validation.

This package provides MCP tools for validating coding plans and code changes
against software engineering best practices.
"""

from .server import main, mcp
from .models import JudgeResponse

__version__ = "1.0.0"
__all__ = ["main", "mcp", "JudgeResponse"]

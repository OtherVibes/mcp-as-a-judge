"""
Workflow management for enhanced MCP as a Judge.

This package contains the workflow guidance system that provides
intelligent next steps for coding tasks.
"""

from .workflow_guidance import WorkflowGuidance, calculate_next_stage

__all__ = ["WorkflowGuidance", "calculate_next_stage"]

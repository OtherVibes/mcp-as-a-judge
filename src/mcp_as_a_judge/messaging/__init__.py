"""
Messaging layer for MCP as a Judge.

This module provides a clean abstraction for sending messages to different
AI providers (MCP sampling, LLM APIs) with automatic fallback and provider
selection based on availability and preferences.
"""

from mcp_as_a_judge.messaging.interface import (
    Message,
    MessagingConfig,
    MessagingProvider,
)
from mcp_as_a_judge.messaging.llm_provider import llm_provider

__all__ = [
    "Message",
    "MessagingConfig",
    "MessagingProvider",
    "llm_provider",
]

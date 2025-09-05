"""
Message format converters for the messaging layer.

This module handles conversion between different message formats:
- Universal Message format (used internally)
- MCP message format (for MCP sampling)
- LLM API format (for direct LLM calls)
"""

from typing import Any

from mcp_as_a_judge.messaging.interface import Message


def messages_to_mcp_format(messages: list[Message]) -> list[Any]:
    """Convert universal messages to MCP format.

    Args:
        messages: List of universal Message objects

    Returns:
        List of MCP-compatible message objects
    """
    from mcp.types import SamplingMessage, TextContent

    # Convert universal messages to proper MCP SamplingMessage objects
    mcp_messages = []

    for msg in messages:
        # Create proper MCP SamplingMessage objects
        # Ensure role is valid for SamplingMessage
        from typing import Literal, cast

        valid_role = cast(
            Literal["user", "assistant"],
            msg.role if msg.role in ["user", "assistant"] else "user",
        )
        mcp_msg = SamplingMessage(
            role=valid_role,
            content=TextContent(type="text", text=msg.content),
        )
        mcp_messages.append(mcp_msg)

    return mcp_messages


def messages_to_llm_format(messages: list[Message]) -> list[dict[str, str]]:
    """Convert universal messages to LLM API format.

    Args:
        messages: List of universal Message objects

    Returns:
        List of dictionaries in LLM API format (OpenAI-compatible)
    """
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def mcp_messages_to_universal(mcp_messages: list[Any]) -> list[Message]:
    """Convert MCP messages to universal format.

    Args:
        mcp_messages: List of MCP message objects (from prompt_loader)

    Returns:
        List of universal Message objects
    """
    universal_messages = []

    for msg in mcp_messages:
        # Handle different possible MCP message structures
        role = None
        content = None

        # Try to extract role
        if hasattr(msg, "role"):
            role = msg.role
        elif hasattr(msg, "type"):
            # Some MCP messages might use 'type' instead of 'role'
            role = msg.type
        else:
            # Default role if not found
            role = "user"

        # Try to extract content
        if hasattr(msg, "content"):
            if hasattr(msg.content, "text"):
                content = msg.content.text
            elif isinstance(msg.content, str):
                content = msg.content
            else:
                content = str(msg.content)
        elif hasattr(msg, "text"):
            content = msg.text
        else:
            content = str(msg)

        # Create universal message
        universal_messages.append(Message(role=role, content=content))

    return universal_messages


def llm_response_to_universal(response: str, role: str = "assistant") -> Message:
    """Convert LLM API response to universal message format.

    Args:
        response: Response text from LLM API
        role: Role for the response message

    Returns:
        Universal Message object
    """
    return Message(role=role, content=response)


def validate_message_conversion(original: list[Any], converted: list[Message]) -> bool:
    """Validate that message conversion preserved essential information.

    Args:
        original: Original messages in any format
        converted: Converted universal messages

    Returns:
        True if conversion appears successful, False otherwise
    """
    if len(original) != len(converted):
        return False

    for _orig, conv in zip(original, converted, strict=False):
        # Check that we have valid role and content
        if not conv.role or not conv.content:
            return False

        # Check that content is not empty or just whitespace
        if not conv.content.strip():
            return False

    return True

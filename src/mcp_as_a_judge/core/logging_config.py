"""
Central logging configuration for MCP as a Judge.

This module provides centralized logging setup with MCP Context integration
when available, falling back to standard logging otherwise.
"""

import logging
import sys
from datetime import datetime
from typing import Any

# Import MCP SDK logging utilities for proper color support
try:
    from mcp.server.fastmcp.utilities.logging import (
        configure_logging,
    )
    from mcp.server.fastmcp.utilities.logging import (
        get_logger as mcp_get_logger,
    )

    MCP_SDK_AVAILABLE = True
except ImportError:
    configure_logging = None  # type: ignore[assignment]
    mcp_get_logger = None  # type: ignore[assignment]
    MCP_SDK_AVAILABLE = False

# Global context reference for MCP integration
_global_context_ref: Any | None = None


def set_context_reference(ctx: Any) -> None:
    """Set global context reference for MCP integration."""
    global _global_context_ref
    _global_context_ref = ctx


class CleanFormatter(logging.Formatter):
    """Clean formatter without ANSI colors - uses MCP SDK logging for proper color support."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with clean output."""
        # Get module name from the actual caller (remove package prefix for cleaner output)
        module_name = record.name
        if module_name.startswith("mcp_as_a_judge."):
            module_name = module_name[len("mcp_as_a_judge.") :]

        # Format timestamp as ISO date
        timestamp = datetime.fromtimestamp(record.created).isoformat()

        # Clean format without ANSI codes - let MCP SDK handle colors
        formatted_message = f"[{record.levelname}] [{module_name}:{record.lineno}] [{timestamp}] {record.getMessage()}"

        # Handle exceptions
        if record.exc_info:
            formatted_message += "\n" + self.formatException(record.exc_info)

        return formatted_message


def setup_logging(level: str = "INFO") -> None:
    """
    Set up centralized logging configuration using MCP SDK.

    Args:
        level: Logging level (default: "INFO")
    """
    if MCP_SDK_AVAILABLE and configure_logging is not None:
        # Use MCP SDK configure_logging for proper color support
        configure_logging(level)  # type: ignore[arg-type]
    else:
        # Fallback to standard logging setup
        # Create custom formatter
        formatter = CleanFormatter()

        # Create handler for stderr (so it's visible in development tools like Cursor)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Clear any existing handlers to avoid duplicates
        root_logger.handlers.clear()

        # Add our custom handler
        root_logger.addHandler(handler)


def configure_application_loggers(level: int = logging.INFO) -> None:
    """
    Configure specific loggers for MCP as a Judge application components.

    Args:
        level: Logging level to set for application loggers
    """
    # List of application-specific loggers to configure
    app_loggers = [
        "mcp_as_a_judge.server",
        "mcp_as_a_judge.core.server_helpers",
        "mcp_as_a_judge.db.conversation_history_service",
        "mcp_as_a_judge.db.providers.in_memory",
        "mcp_as_a_judge.db.providers.sqlite_provider",
        "mcp_as_a_judge.messaging",
        "mcp_as_a_judge.llm",
        "mcp_as_a_judge.config",
        "mcp_as_a_judge.workflow.workflow_guidance",
        "mcp_as_a_judge.tasks.manager",
    ]

    # Set level for each application logger
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


class ContextAwareLogger:
    """Logger that automatically uses MCP Context when available."""

    def __init__(self, name: str):
        """Initialize logger with a name."""
        self.name = name
        # Use MCP SDK logger for fallback (proper color support)
        if MCP_SDK_AVAILABLE:
            # Clean name for MCP SDK
            clean_name = name
            if name.startswith("mcp_as_a_judge."):
                clean_name = name[len("mcp_as_a_judge.") :]
            elif name == "__main__":
                clean_name = "server"
            self._fallback_logger = mcp_get_logger(clean_name)
        else:
            self._fallback_logger = logging.getLogger(name)

    async def info(self, message: str) -> None:
        """Log info message using Context if available, MCP SDK logging otherwise."""
        global _global_context_ref
        if _global_context_ref is not None:
            await _global_context_ref.info(message)
        else:
            self._fallback_logger.info(message)

    async def debug(self, message: str) -> None:
        """Log debug message using Context if available, MCP SDK logging otherwise."""
        global _global_context_ref
        if _global_context_ref is not None:
            await _global_context_ref.debug(message)
        else:
            self._fallback_logger.debug(message)

    async def warning(self, message: str) -> None:
        """Log warning message using Context if available, MCP SDK logging otherwise."""
        global _global_context_ref
        if _global_context_ref is not None:
            await _global_context_ref.warning(message)
        else:
            self._fallback_logger.warning(message)

    async def error(self, message: str) -> None:
        """Log error message using Context if available, MCP SDK logging otherwise."""
        global _global_context_ref
        if _global_context_ref is not None:
            await _global_context_ref.error(message)
        else:
            self._fallback_logger.error(message)

    # Synchronous methods for backward compatibility
    def info_sync(self, message: str) -> None:
        """Synchronous info logging using MCP SDK."""
        self._fallback_logger.info(message)

    def debug_sync(self, message: str) -> None:
        """Synchronous debug logging using MCP SDK."""
        self._fallback_logger.debug(message)

    def warning_sync(self, message: str) -> None:
        """Synchronous warning logging using MCP SDK."""
        self._fallback_logger.warning(message)

    def error_sync(self, message: str) -> None:
        """Synchronous error logging using MCP SDK."""
        self._fallback_logger.error(message)


def get_context_aware_logger(name: str) -> ContextAwareLogger:
    """
    Get a context-aware logger that automatically uses MCP Context when available.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        ContextAwareLogger instance
    """
    return ContextAwareLogger(name)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    This is a convenience function that ensures consistent logger naming
    across the application.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_startup_message(config: Any) -> None:
    """
    Log application startup message with configuration details.

    Args:
        config: Application configuration object
    """
    logger = get_logger("mcp_as_a_judge.server")
    logger.info("MCP Judge server starting with conversation history logging enabled")
    logger.info(
        f"Configuration: max_session_records={config.database.max_session_records}"
    )


def _truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to a maximum length with ellipsis if needed.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated text with '...' if it was longer than max_length
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def log_tool_execution(
    tool_name: str, session_id: str, additional_info: str = ""
) -> None:
    """
    Log tool execution start with consistent formatting.

    Args:
        tool_name: Name of the tool being executed
        session_id: Session identifier
        additional_info: Additional information to log (will be truncated if too long)
    """
    logger = get_logger("mcp_as_a_judge.server")

    logger.info(f"{tool_name} called for session {_truncate_text(session_id)}")

    if additional_info:
        # Truncate additional info to prevent overly long log lines
        truncated_info = _truncate_text(additional_info, 200)
        logger.info(f"   {truncated_info}")


def log_error(error: Exception, context: str = "") -> None:
    """
    Log error with consistent formatting and context.

    Args:
        error: Exception that occurred
        context: Additional context about where the error occurred (will be truncated if too long)
    """
    logger = get_logger("mcp_as_a_judge.server")

    # Truncate error message and context to prevent overly long log lines
    error_msg = _truncate_text(str(error), 300)

    if context:
        truncated_context = _truncate_text(context, 100)
        logger.error(f"Error in {truncated_context}: {error_msg}")
    else:
        logger.error(f"Error: {error_msg}")

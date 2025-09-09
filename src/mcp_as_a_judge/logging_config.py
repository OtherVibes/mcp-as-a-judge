"""
Central logging configuration for MCP as a Judge.

This module provides centralized logging setup with colored output and
consistent formatting across the entire application.
"""

import logging
import sys
from datetime import datetime
from typing import Any, ClassVar


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels and formats messages."""

    # ANSI color codes
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"  # Reset color

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and custom format."""
        # Get color for log level
        level_color = self.COLORS.get(record.levelname, "")

        # Format: [level_with_color] [module:linenumber] [iso-date] [message]
        colored_level = f"{level_color}{record.levelname}{self.RESET}"

        # Get module name (remove package prefix for cleaner output)
        module_name = record.name
        if module_name.startswith("mcp_as_a_judge."):
            module_name = module_name[len("mcp_as_a_judge.") :]

        # Format timestamp as ISO date
        timestamp = datetime.fromtimestamp(record.created).isoformat()

        # Build the formatted message
        formatted_message = f"[{colored_level}] [{module_name}:{record.lineno}] [{timestamp}] {record.getMessage()}"

        # Handle exceptions
        if record.exc_info:
            formatted_message += "\n" + self.formatException(record.exc_info)

        return formatted_message


def setup_logging(level: int = logging.INFO) -> None:
    """
    Set up centralized logging configuration for the entire application.

    Args:
        level: Logging level (default: INFO)
    """
    # Create custom formatter
    formatter = ColoredFormatter()

    # Create handler for stderr (so it's visible in development tools like Cursor)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add our custom handler
    root_logger.addHandler(handler)

    # Configure specific loggers for our application
    configure_application_loggers(level)


def configure_application_loggers(level: int = logging.INFO) -> None:
    """
    Configure specific loggers for MCP as a Judge application components.

    Args:
        level: Logging level to set for application loggers
    """
    # List of application-specific loggers to configure
    app_loggers = [
        "mcp_as_a_judge.server",
        "mcp_as_a_judge.server_helpers",
        "mcp_as_a_judge.conversation_history_service",
        "mcp_as_a_judge.db.conversation_history_service",
        "mcp_as_a_judge.db.providers.in_memory",
        "mcp_as_a_judge.db.providers.sqlite_provider",
        "mcp_as_a_judge.messaging",
        "mcp_as_a_judge.llm_client",
        "mcp_as_a_judge.config",
        "mcp_as_a_judge.workflow.workflow_guidance",
        "mcp_as_a_judge.coding_task_manager",
    ]

    # Set level for each application logger
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


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
    logger.info(
        "🚀 MCP Judge server starting with conversation history logging enabled"
    )
    logger.info(
        f"📊 Configuration: max_session_records={config.database.max_session_records}"
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

    # Map tool names to emojis for better visibility
    tool_emojis = {
        "build_workflow": "🔧",
        "judge_coding_plan": "⚖️",
        "judge_code_change": "🔍",
        "raise_obstacle": "🚧",
        "raise_missing_requirements": "❓",
    }

    emoji = tool_emojis.get(tool_name, "🛠️")
    logger.info(f"{emoji} {tool_name} called for session {_truncate_text(session_id)}")

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
        logger.error(f"❌ Error in {truncated_context}: {error_msg}")
    else:
        logger.error(f"❌ Error: {error_msg}")

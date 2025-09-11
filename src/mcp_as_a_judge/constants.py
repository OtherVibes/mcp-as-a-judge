"""
Constants for MCP as a Judge.

This module contains all static configuration values used throughout the application.
"""

# LLM Configuration
MAX_TOKENS = (
    25000  # Maximum tokens for all LLM requests - increased for comprehensive responses
)
DEFAULT_TEMPERATURE = 0.1  # Default temperature for LLM requests
DEFAULT_REASONING_EFFORT = (
    "low"  # Default reasoning effort level - lowest for speed and efficiency
)

# Timeout Configuration
DEFAULT_TIMEOUT = 30  # Default timeout in seconds for operations

# Database Configuration
DATABASE_URL = "sqlite://:memory:"
MAX_SESSION_RECORDS = 20  # Maximum records to keep per session (FIFO)
RECORD_RETENTION_DAYS = 1

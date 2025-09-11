"""
Constants for MCP as a Judge.

This module contains all static configuration values used throughout the application.
"""

# LLM Configuration
MAX_TOKENS = 10000  # Maximum tokens for all LLM requests
DEFAULT_TEMPERATURE = 0.1  # Default temperature for LLM requests

# Timeout Configuration
DEFAULT_TIMEOUT = 30  # Default timeout in seconds for operations

# Database Configuration
DATABASE_URL = "sqlite://:memory:"
MAX_SESSION_RECORDS = 20  # Maximum records to keep per session (FIFO)
MAX_TOTAL_SESSIONS = 50  # Maximum total sessions to keep (LRU cleanup)

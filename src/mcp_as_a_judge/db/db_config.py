"""
Database configuration for MCP as a Judge.

This module handles database configuration logic, including provider detection
and configuration classes.
"""

from mcp_as_a_judge.core.constants import (
    DATABASE_URL,
    MAX_SESSION_RECORDS,
    MAX_TOTAL_SESSIONS,
)


def get_database_provider_from_url(url: str) -> str:
    """
    Determine database provider from URL.

    Args:
        url: Database connection URL

    Returns:
        Provider name based on URL scheme

    Examples:
        "" or None -> "in_memory" (SQLite in-memory)
        "sqlite://:memory:" -> "in_memory" (SQLite in-memory)
        "sqlite:///path/to/file.db" -> "sqlite" (SQLite file)
        "postgresql://..." -> "postgresql"
        "mysql://..." -> "mysql"
    """
    if not url or url.strip() == "":
        return "in_memory"

    url_lower = url.lower().strip()

    # SQLite in-memory
    if url_lower == "sqlite://:memory:" or url_lower == ":memory:":
        return "in_memory"

    # SQLite file
    elif url_lower.startswith("sqlite://") or url_lower.endswith(".db"):
        return "sqlite"

    # PostgreSQL
    elif url_lower.startswith("postgresql://") or url_lower.startswith("postgres://"):
        return "postgresql"

    # MySQL
    elif url_lower.startswith("mysql://") or url_lower.startswith("mysql+"):
        return "mysql"

    else:
        # Default to in_memory for unknown URLs
        return "in_memory"


class DatabaseConfig:
    """Database configuration using constants."""

    def __init__(self) -> None:
        self.url = DATABASE_URL
        self.max_session_records = MAX_SESSION_RECORDS
        self.max_total_sessions = MAX_TOTAL_SESSIONS


class Config:
    """Main configuration using constants."""

    def __init__(self) -> None:
        self.database = DatabaseConfig()


def load_config() -> Config:
    """
    Load configuration from environment variables and constants.

    Returns:
        Config object with loaded settings
    """
    return Config()

"""
Configuration management for MCP as a Judge.

This module handles loading and managing configuration from various sources
including config files, environment variables, and defaults.
"""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .models import DatabaseConfig


class Config(BaseModel):
    """Main configuration model for the application."""
    
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    enable_llm_fallback: bool = Field(
        default=True,
        description="Whether to enable LLM fallback when MCP sampling is not available"
    )


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_path: Path to config file. If None, looks for config.json in current directory
        
    Returns:
        Config object with loaded settings
    """
    # Default configuration
    config_data = {}
    
    # Try to load from config file
    if config_path is None:
        config_path = "config.json"
    
    config_file = Path(config_path)
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
    
    # Override with environment variables if present
    db_provider = os.getenv("MCP_JUDGE_DB_PROVIDER")
    if db_provider:
        if "database" not in config_data:
            config_data["database"] = {}
        config_data["database"]["provider"] = db_provider
    
    db_url = os.getenv("MCP_JUDGE_DB_URL")
    if db_url:
        if "database" not in config_data:
            config_data["database"] = {}
        config_data["database"]["url"] = db_url
    
    max_context = os.getenv("MCP_JUDGE_MAX_CONTEXT_RECORDS")
    if max_context:
        if "database" not in config_data:
            config_data["database"] = {}
        try:
            config_data["database"]["max_context_records"] = int(max_context)
        except ValueError:
            print(f"Warning: Invalid value for MCP_JUDGE_MAX_CONTEXT_RECORDS: {max_context}")
    
    llm_fallback = os.getenv("MCP_JUDGE_ENABLE_LLM_FALLBACK")
    if llm_fallback:
        config_data["enable_llm_fallback"] = llm_fallback.lower() in ("true", "1", "yes", "on")
    
    return Config(**config_data)


def create_default_config_file(config_path: str = "config.json") -> None:
    """
    Create a default configuration file.
    
    Args:
        config_path: Path where to create the config file
    """
    default_config = {
        "database": {
            "provider": "in_memory",
            "url": "",
            "max_context_records": 10
        },
        "enable_llm_fallback": True
    }
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"Created default configuration file: {config_path}")


def get_database_provider_from_url(url: str) -> str:
    """
    Determine database provider from URL.
    
    Args:
        url: Database connection URL
        
    Returns:
        Provider name: 'sqlite', 'postgresql', or 'in_memory'
    """
    if not url:
        return "in_memory"
    
    url_lower = url.lower()
    if url_lower.startswith("sqlite://") or url_lower.endswith(".db"):
        return "sqlite"
    elif url_lower.startswith("postgresql://") or url_lower.startswith("postgres://"):
        return "postgresql"
    else:
        # Default to in_memory for unknown URLs
        return "in_memory"

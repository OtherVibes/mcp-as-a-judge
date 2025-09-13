"""
LLM integration module for MCP as a Judge.

This module provides LLM API key support as a fallback when MCP sampling
is not available. It uses LiteLLM to support multiple providers and includes
vendor detection from API key patterns.
"""

import os
import re
from enum import Enum

from pydantic import BaseModel, Field

from mcp_as_a_judge.core.constants import DEFAULT_TEMPERATURE, MAX_TOKENS


class LLMVendor(str, Enum):
    """Supported LLM vendors with their API key patterns."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    AWS_BEDROCK = "aws_bedrock"
    VERTEX_AI = "vertex_ai"
    GROQ = "groq"
    MISTRAL = "mistral"
    XAI = "xai"
    OPENROUTER = "openrouter"
    UNKNOWN = "unknown"


class LLMConfig(BaseModel):
    """Configuration for LLM API integration.

    This configuration is used when MCP sampling is not available,
    providing a fallback mechanism for AI-powered evaluations.
    """

    api_key: str | None = Field(
        default=None,
        description="LLM API key - used only when MCP sampling is NOT available",
    )
    model_name: str | None = Field(
        default=None,
        description="Model name to use (if not specified, uses vendor default)",
    )
    vendor: LLMVendor | None = Field(
        default=None, description="Detected or specified LLM vendor"
    )
    max_tokens: int = Field(
        default=MAX_TOKENS, description="Maximum tokens for LLM responses"
    )
    temperature: float = Field(
        default=DEFAULT_TEMPERATURE,
        description="Temperature for LLM responses (0.0-1.0) - Low for coding tasks",
    )


# API key patterns for vendor detection (ordered by specificity)
API_KEY_PATTERNS = {
    # Most specific patterns first
    LLMVendor.ANTHROPIC: re.compile(r"^sk-ant-[a-zA-Z0-9_-]{20,}"),
    LLMVendor.GOOGLE: re.compile(r"^AIza[a-zA-Z0-9_-]{35}"),
    LLMVendor.GROQ: re.compile(r"^gsk_[a-zA-Z0-9]{50,}"),
    LLMVendor.XAI: re.compile(r"^xai-[a-zA-Z0-9]{40,}"),
    LLMVendor.OPENROUTER: re.compile(r"^sk-or-[a-zA-Z0-9_-]{48}"),
    LLMVendor.OPENAI: re.compile(r"^sk-[a-zA-Z0-9]{20,}"),
    # Azure uses various patterns, often similar to OpenAI
    LLMVendor.AZURE: re.compile(r"^[a-f0-9]{32}$"),
    # AWS Bedrock uses AWS credentials (detected by special marker)
    LLMVendor.AWS_BEDROCK: re.compile(r"^aws-credentials$"),
    # Vertex AI uses Service Account JSON (detected by special marker)
    LLMVendor.VERTEX_AI: re.compile(r"^service-account-json$"),
    # Mistral uses more specific patterns (not just any 32+ chars)
    LLMVendor.MISTRAL: re.compile(r"^[a-f0-9]{64}$|^mistral-[a-zA-Z0-9]{32,}"),
}

# Default models per vendor - Optimized for speed and performance
DEFAULT_MODELS = {
    LLMVendor.OPENAI: "gpt-4.1",  # Fast and reliable model optimized for speed
    LLMVendor.ANTHROPIC: "claude-sonnet-4-20250514",  # High-performance with exceptional reasoning
    LLMVendor.GOOGLE: "gemini-2.5-pro",  # Most advanced model with built-in thinking
    LLMVendor.AZURE: "gpt-4.1",  # Same as OpenAI but via Azure
    LLMVendor.AWS_BEDROCK: "anthropic.claude-sonnet-4-20250514-v1:0",  # Aligned with Anthropic
    LLMVendor.VERTEX_AI: "gemini-2.5-pro",  # Enterprise Gemini via Google Cloud
    LLMVendor.GROQ: "deepseek-r1",  # Best reasoning model with speed advantage
    LLMVendor.OPENROUTER: "deepseek/deepseek-r1",  # Best reasoning model available
    LLMVendor.MISTRAL: "pixtral-large",  # Most advanced model (124B params) built on Mistral Large 2
    LLMVendor.XAI: "grok-code-fast-1",  # Latest coding-focused model with reasoning (Aug 2025)
    LLMVendor.UNKNOWN: "gpt-4.1",  # Fallback to fast and reliable model
}


def detect_vendor_from_api_key(api_key: str) -> LLMVendor:
    """Detect LLM vendor from API key pattern.

    Args:
        api_key: The API key to analyze

    Returns:
        Detected LLMVendor or UNKNOWN if pattern doesn't match
    """
    if not api_key:
        return LLMVendor.UNKNOWN

    for vendor, pattern in API_KEY_PATTERNS.items():
        if pattern.match(api_key):
            return vendor

    return LLMVendor.UNKNOWN


def get_default_model(vendor: LLMVendor) -> str:
    """Get default model for a vendor.

    Args:
        vendor: The LLM vendor

    Returns:
        Default model name for the vendor
    """
    return DEFAULT_MODELS.get(vendor, DEFAULT_MODELS[LLMVendor.UNKNOWN])


def create_llm_config(
    api_key: str | None = None,
    model_name: str | None = None,
    vendor: LLMVendor | None = None,
    **kwargs: str,
) -> LLMConfig:
    """Create LLM configuration with vendor detection and defaults.

    Args:
        api_key: LLM API key
        model_name: Model name (optional, uses vendor default if not provided)
        vendor: LLM vendor (optional, auto-detected from API key if not provided)
        **kwargs: Additional configuration options

    Returns:
        Configured LLMConfig instance
    """
    # Auto-detect vendor if not provided
    if vendor is None and api_key:
        vendor = detect_vendor_from_api_key(api_key)
    elif vendor is None:
        vendor = LLMVendor.UNKNOWN

    # Use default model if not provided
    if model_name is None:
        model_name = get_default_model(vendor)

    return LLMConfig(api_key=api_key, model_name=model_name, vendor=vendor)


def load_llm_config_from_env() -> LLMConfig | None:
    """Load LLM configuration from environment variables.

    Uses LLM_API_KEY environment variable and automatically detects
    the vendor from the API key format.

    Returns:
        LLMConfig if LLM_API_KEY found in environment, None otherwise
    """
    # Check for the single LLM_API_KEY environment variable
    api_key = os.getenv("LLM_API_KEY")
    if api_key:
        # Get model name from environment if specified
        model_name = os.getenv("LLM_MODEL_NAME")

        return create_llm_config(api_key=api_key, model_name=model_name)

    return None

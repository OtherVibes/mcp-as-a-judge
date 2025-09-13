"""
Helper functions for the MCP as a Judge server.

This module contains utility functions used by the server for JSON processing,
dynamic model generation, validation, and LLM configuration.
"""

import json

from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

from mcp_as_a_judge.core.constants import MAX_TOKENS
from mcp_as_a_judge.core.logging_config import get_logger
from mcp_as_a_judge.llm.llm_integration import load_llm_config_from_env
from mcp_as_a_judge.messaging.llm_provider import llm_provider
from mcp_as_a_judge.prompting.loader import create_separate_messages


def get_session_id(ctx: Context) -> str:
    """Extract session_id from context, with fallback to default."""
    return getattr(ctx, "session_id", "default_session")


def initialize_llm_configuration() -> None:
    """Initialize LLM configuration from environment variables.

    This function loads LLM configuration from environment variables and
    configures the LLM manager if a valid configuration is found.
    Logs status messages to inform users about the configuration state.
    """
    logger = get_logger(__name__)
    # Do not auto-configure LLM from environment during server startup to keep
    # tests deterministic and avoid unintended provider availability.
    # Callers can configure llm_manager explicitly if needed.
    llm_config = load_llm_config_from_env()
    if llm_config:
        logger.info(
            "LLM configuration detected in environment (not auto-enabled during startup)."
        )
    else:
        logger.info(
            "No LLM API key found in environment. MCP sampling will be required."
        )


def extract_json_from_response(response_text: str) -> str:
    """Extract JSON content from LLM response by finding first { and last }.

    LLMs often return JSON wrapped in markdown code blocks, explanatory text,
    or other formatting. This function extracts just the JSON object content.

    Args:
        response_text: Raw LLM response text

    Returns:
        Extracted JSON string ready for parsing

    Raises:
        ValueError: If no JSON object is found in the response
    """
    first_brace = response_text.find("{")
    last_brace = response_text.rfind("}")

    if first_brace == -1 or last_brace == -1 or first_brace >= last_brace:
        response_info = {
            "length": len(response_text),
            "is_empty": len(response_text.strip()) == 0,
            "first_100_chars": response_text[:100] if response_text else "None",
            "contains_json_markers": "{" in response_text and "}" in response_text,
        }
        raise ValueError(
            f"No valid JSON object found in response. "
            f"Response info: {response_info}. "
            f"Full response: '{response_text}'"
        )

    json_content = response_text[first_brace : last_brace + 1]
    return json_content


async def generate_validation_error_message(
    validation_issue: str,
    context: str,
    ctx: Context,
) -> str:
    """Generate a descriptive error message using AI sampling for validation failures."""
    try:
        from mcp_as_a_judge.models import (
            SystemVars,
            ValidationErrorUserVars,
        )

        system_vars = SystemVars(max_tokens=MAX_TOKENS)
        user_vars = ValidationErrorUserVars(
            validation_issue=validation_issue, context=context
        )

        messages = create_separate_messages(
            "system/validation_error.md",
            "user/validation_error.md",
            system_vars,
            user_vars,
        )

        response_text = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=MAX_TOKENS,
            prefer_sampling=True,  # gitleaks:allow
        )
        return response_text.strip()

    except Exception:
        return validation_issue


async def generate_dynamic_elicitation_model(
    context: str,
    information_needed: str,
    current_understanding: str,
    ctx: Context,
) -> type[BaseModel]:
    """Generate a dynamic Pydantic model for elicitation based on context.

    This function uses LLM to generate field definitions and creates a proper
    Pydantic BaseModel class that's compatible with MCP elicitation.

    Args:
        context: Context about what information needs to be gathered
        information_needed: Specific description of what information is needed
        current_understanding: What we currently understand about the situation
        ctx: MCP context for LLM communication

    Returns:
        Dynamically created Pydantic BaseModel class
    """
    try:
        from mcp_as_a_judge.models import DynamicSchemaUserVars, SystemVars

        system_vars = SystemVars(max_tokens=MAX_TOKENS)
        user_vars = DynamicSchemaUserVars(
            context=context,
            information_needed=information_needed,
            current_understanding=current_understanding,
        )

        messages = create_separate_messages(
            "system/dynamic_schema.md", "user/dynamic_schema.md", system_vars, user_vars
        )

        # Use LLM to generate field definitions
        schema_text = await llm_provider.send_message(
            messages=messages,
            ctx=ctx,
            max_tokens=MAX_TOKENS,
            prefer_sampling=True,  # gitleaks:allow
        )

        # Parse the field definitions JSON
        fields_json = extract_json_from_response(schema_text)
        fields_dict = json.loads(fields_json)

        # Convert field definitions to Pydantic model
        return create_pydantic_model_from_fields(fields_dict)

    except Exception:
        # If dynamic generation fails, re-raise the exception
        # All fields MUST be resolved by LLM - no static fallback
        raise


def create_pydantic_model_from_fields(fields_dict: dict) -> type[BaseModel]:
    """Convert field definitions to a Pydantic BaseModel class.

    Args:
        fields_dict: Dictionary where keys are field names and values are objects
                    with "required" (bool) and "description" (str) properties

    Returns:
        Dynamically created Pydantic BaseModel class
    """
    # Build field definitions for the Pydantic model
    field_definitions = {}

    for field_name, field_config in fields_dict.items():
        # Extract configuration from LLM-generated field definition
        # Handle cases where LLM returns boolean instead of dict
        if isinstance(field_config, dict):
            is_required = field_config.get("required", False)
            description = field_config.get(
                "description", field_name.replace("_", " ").title()
            )
        elif isinstance(field_config, bool):
            # LLM returned boolean - treat as required flag
            is_required = field_config
            description = field_name.replace("_", " ").title()
        else:
            # LLM returned something else (string, etc.) - treat as description
            is_required = False
            description = (
                str(field_config)
                if field_config
                else field_name.replace("_", " ").title()
            )

        # All fields are strings (text input) as per MCP elicitation constraints
        # MCP elicitation only supports primitive types, no unions like str | None
        if is_required:
            field_definitions[field_name] = (str, Field(description=description))
        else:
            # Use empty string as default for optional fields (primitive type only)
            field_definitions[field_name] = (
                str,
                Field(default="", description=description),
            )

    # Create the dynamic model class
    dynamic_elicitation_model = type(
        "DynamicElicitationModel",
        (BaseModel,),
        {
            "__annotations__": {
                name: field_def[0] for name, field_def in field_definitions.items()
            },
            **{name: field_def[1] for name, field_def in field_definitions.items()},
        },
    )

    return dynamic_elicitation_model


# (Removed rule-based decision extraction and gating to keep HITL LLM-driven)

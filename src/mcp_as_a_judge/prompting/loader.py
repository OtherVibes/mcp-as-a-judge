"""Prompt loader utility for loading and rendering Jinja2 templates."""

from pathlib import Path
from typing import Any, cast

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files  # type: ignore[import-not-found,no-redef]

from jinja2 import Environment, FileSystemLoader, Template
from mcp.types import SamplingMessage, TextContent
from pydantic import BaseModel


class PromptLoader:
    """Loads and renders prompt templates using Jinja2."""

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize the prompt loader.

        Args:
            prompts_dir: Directory containing prompt templates.
                        Defaults to src/prompts relative to this file.
        """
        if prompts_dir is None:
            # Use importlib.resources to get the prompts directory from the package
            prompts_resource = files("mcp_as_a_judge") / "prompts"
            prompts_dir = Path(str(prompts_resource))

        self.prompts_dir = prompts_dir
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # nosec B701 - Safe for prompt templates (not HTML)  # noqa: S701
        )

    def load_template(self, template_name: str) -> Template:
        """Load a Jinja2 template by name.

        Args:
            template_name: Name of the template file (e.g., 'judge_coding_plan.md')

        Returns:
            Jinja2 Template object

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        try:
            return self.env.get_template(template_name)
        except Exception as e:
            raise FileNotFoundError(
                f"Template '{template_name}' not found in {self.prompts_dir}"
            ) from e

    def render_prompt(self, template_name: str, **kwargs: Any) -> str:
        """Load and render a prompt template with the given variables.

        Args:
            template_name: Name of the template file
            **kwargs: Variables to pass to the template

        Returns:
            Rendered prompt string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template = self.load_template(template_name)
        return cast(str, template.render(**kwargs))  # type: ignore[redundant-cast,unused-ignore]


# Global instance for easy access
prompt_loader = PromptLoader()


def create_separate_messages(
    system_template: str,
    user_template: str,
    system_vars: BaseModel,
    user_vars: BaseModel,
) -> list[SamplingMessage]:
    """Create separate system and user messages from templates.

    This function creates properly separated messages with distinct roles:
    - System template → SamplingMessage with role "assistant" (system instructions)
    - User template → SamplingMessage with role "user" (user request)

    Args:
        system_template: Name of the system message template file
        user_template: Name of the user message template file
        system_vars: Pydantic model containing variables for system template
        user_vars: Pydantic model containing variables for user template

    Returns:
        List of SamplingMessage objects with separate system and user messages
    """
    # Render system prompt with system variables
    system_content = prompt_loader.render_prompt(
        system_template, **system_vars.model_dump(exclude_none=True)
    )

    # Render user prompt with user variables
    user_content = prompt_loader.render_prompt(
        user_template, **user_vars.model_dump(exclude_none=True)
    )

    return [
        # System instructions as assistant message
        SamplingMessage(
            role="assistant",
            content=TextContent(type="text", text=system_content),
        ),
        # User request as user message
        SamplingMessage(
            role="user",
            content=TextContent(type="text", text=user_content),
        ),
    ]

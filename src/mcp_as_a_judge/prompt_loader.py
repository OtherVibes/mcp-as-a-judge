"""Prompt loader utility for loading and rendering Jinja2 templates."""

import sys
from pathlib import Path
from typing import Any, cast

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
            prompts_dir = self._find_prompts_directory()

        self.prompts_dir = prompts_dir
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # nosec B701 - Safe for prompt templates (not HTML)  # noqa: S701
        )

    def _find_prompts_directory(self) -> Path:
        """Find the prompts directory in development or installed package.

        Returns:
            Path to the prompts directory

        Raises:
            FileNotFoundError: If prompts directory cannot be found
        """
        # Try development location first (src/prompts relative to this file)
        current_dir = Path(__file__).parent
        dev_prompts_dir = current_dir.parent / "prompts"

        if dev_prompts_dir.exists():
            return dev_prompts_dir

        # Try installed package location (shared data)
        # When installed via pip/uv, shared data goes to site-packages/
        try:
            import mcp_as_a_judge
            package_dir = Path(mcp_as_a_judge.__file__).parent.parent
            installed_prompts_dir = package_dir / "prompts"

            if installed_prompts_dir.exists():
                return installed_prompts_dir
        except (ImportError, AttributeError):
            pass

        # Try alternative installed locations
        possible_locations = [
            # Standard site-packages location
            Path(sys.prefix) / "share" / "mcp-as-a-judge" / "prompts",
            # Local user installation
            Path.home() / ".local" / "share" / "mcp-as-a-judge" / "prompts",
            # UV tool installation
            Path.home() / ".local" / "share" / "uv" / "tools" / "mcp-as-a-judge" / "prompts",
        ]

        for location in possible_locations:
            if location.exists():
                return location

        # Last resort: look for prompts directory anywhere in the Python path
        for path_str in sys.path:
            path = Path(path_str)
            prompts_path = path / "prompts"
            if prompts_path.exists() and (prompts_path / "system").exists():
                return prompts_path

        raise FileNotFoundError(
            f"Could not find prompts directory. Tried:\n"
            f"- Development: {dev_prompts_dir}\n"
            f"- Installed locations: {possible_locations}\n"
            f"Please ensure the package is properly installed or run from the development directory."
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
        system_template, **system_vars.model_dump()
    )

    # Render user prompt with user variables
    user_content = prompt_loader.render_prompt(
        user_template, **user_vars.model_dump()
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

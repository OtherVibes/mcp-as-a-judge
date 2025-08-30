"""Prompt loader utility for loading and rendering Jinja2 templates."""

from pathlib import Path
from typing import Any, cast

from jinja2 import Environment, FileSystemLoader, Template


class PromptLoader:
    """Loads and renders prompt templates using Jinja2."""

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize the prompt loader.

        Args:
            prompts_dir: Directory containing prompt templates.
                        Defaults to src/prompts relative to this file.
        """
        if prompts_dir is None:
            # Default to src/prompts directory
            current_dir = Path(__file__).parent
            prompts_dir = current_dir.parent / "prompts"

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

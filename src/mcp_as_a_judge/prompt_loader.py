"""Prompt loader utility for loading and rendering Jinja2 templates."""

from pathlib import Path
from typing import Any, Dict

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
            raise FileNotFoundError(f"Template '{template_name}' not found in {self.prompts_dir}") from e

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
        return template.render(**kwargs)

    def render_judge_coding_plan(
        self,
        user_requirements: str,
        plan: str,
        design: str,
        research: str,
        context: str = "",
        response_schema: str = "",
    ) -> str:
        """Render the judge coding plan prompt.
        
        Args:
            user_requirements: User's requirements
            plan: Coding plan to evaluate
            design: System design
            research: Research findings
            context: Additional context
            response_schema: JSON schema for response format
            
        Returns:
            Rendered prompt string
        """
        return self.render_prompt(
            "judge_coding_plan.md",
            user_requirements=user_requirements,
            plan=plan,
            design=design,
            research=research,
            context=context,
            response_schema=response_schema,
        )

    def render_judge_code_change(
        self,
        user_requirements: str,
        code_change: str,
        file_path: str,
        change_description: str,
        response_schema: str = "",
    ) -> str:
        """Render the judge code change prompt.
        
        Args:
            user_requirements: User's requirements
            code_change: Code content to review
            file_path: Path to the file
            change_description: Description of the change
            response_schema: JSON schema for response format
            
        Returns:
            Rendered prompt string
        """
        return self.render_prompt(
            "judge_code_change.md",
            user_requirements=user_requirements,
            code_change=code_change,
            file_path=file_path,
            change_description=change_description,
            response_schema=response_schema,
        )

    def render_research_validation(
        self,
        user_requirements: str,
        plan: str,
        design: str,
        research: str,
    ) -> str:
        """Render the research validation prompt.
        
        Args:
            user_requirements: User's requirements
            plan: Coding plan
            design: System design
            research: Research to validate
            
        Returns:
            Rendered prompt string
        """
        return self.render_prompt(
            "research_validation.md",
            user_requirements=user_requirements,
            plan=plan,
            design=design,
            research=research,
        )


# Global instance for easy access
prompt_loader = PromptLoader()

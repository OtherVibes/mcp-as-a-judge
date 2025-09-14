"""Tool description provider for loading descriptions from local markdown files.

Adds limited Jinja context variables with JSON schemas from core response models
so descriptions can embed authoritative schemas without duplication.
"""

import json
from pathlib import Path
from typing import cast

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files  # type: ignore[import-not-found,no-redef]

from jinja2 import Environment, FileSystemLoader

from mcp_as_a_judge.tool_description.interface import ToolDescriptionProvider


class LocalStorageProvider(ToolDescriptionProvider):
    """Provides tool descriptions loaded from local markdown files.

    This provider loads tool descriptions from markdown files in the
    tool_descriptions directory, following the same pattern as the
    existing prompt loader system.
    """

    def __init__(self, descriptions_dir: Path | None = None):
        """Initialize the tool description provider.

        Args:
            descriptions_dir: Directory containing tool description files.
                            Defaults to src/mcp_as_a_judge/prompts/tool_descriptions
        """
        if descriptions_dir is None:
            # Use importlib.resources to get the tool_descriptions directory from the package
            descriptions_resource = (
                files("mcp_as_a_judge") / "prompts" / "tool_descriptions"
            )
            descriptions_dir = Path(str(descriptions_resource))

        self.descriptions_dir = descriptions_dir

        # Configure Jinja loader to support shared includes referenced like 'shared/foo.md'
        # Search both the tool_descriptions directory and the parent 'prompts' directory
        prompts_root = descriptions_dir.parent
        self.env = Environment(
            loader=FileSystemLoader([str(descriptions_dir), str(prompts_root)]),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # nosec B701 - Safe for description files (not HTML)  # noqa: S701
        )

        # Cache for loaded descriptions to avoid repeated file I/O
        self._description_cache: dict[str, str] = {}

        # Provide limited, stable context variables for template rendering
        # Import here to avoid module-level import cycles
        try:
            from mcp_as_a_judge.models.enhanced_responses import (
                JudgeResponse,
                TaskAnalysisResult,
                TaskCompletionResult,
            )

            self._context_vars = {
                # Pretty-printed JSON strings for embedding in docs
                "JUDGE_RESPONSE_SCHEMA": json.dumps(
                    JudgeResponse.model_json_schema(), indent=2
                ),
                "TASK_ANALYSIS_RESULT_SCHEMA": json.dumps(
                    TaskAnalysisResult.model_json_schema(), indent=2
                ),
                "TASK_COMPLETION_RESULT_SCHEMA": json.dumps(
                    TaskCompletionResult.model_json_schema(), indent=2
                ),
            }
        except Exception:
            # Fallback to empty context if models are unavailable at import time
            self._context_vars = {}

    def get_description(self, tool_name: str) -> str:
        """Get tool description for the specified tool.

        Args:
            tool_name: Name of the tool (e.g., 'build_workflow')

        Returns:
            Tool description string

        Raises:
            FileNotFoundError: If description file doesn't exist
        """
        # Check cache first
        if tool_name in self._description_cache:
            return self._description_cache[tool_name]

        # Load from file
        description = self._load_description_file(tool_name)

        # Cache the result
        self._description_cache[tool_name] = description

        return description

    def clear_cache(self) -> None:
        """Clear the description cache.

        Useful for testing or when description files are updated at runtime.
        """
        self._description_cache.clear()

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names.

        Returns:
            List of tool names that have descriptions available
        """
        try:
            # List all .md files in the descriptions directory
            tool_files = []
            for file_path in self.descriptions_dir.glob("*.md"):
                tool_name = file_path.stem  # Remove .md extension
                tool_files.append(tool_name)
            return sorted(tool_files)
        except Exception:
            # Return empty list if directory doesn't exist or can't be read
            return []

    @property
    def provider_type(self) -> str:
        """Get the provider type identifier."""
        return "local_storage"

    def _load_description_file(self, tool_name: str) -> str:
        """Load description from markdown file.

        Args:
            tool_name: Name of the tool

        Returns:
            Raw description content from the markdown file

        Raises:
            FileNotFoundError: If description file doesn't exist
        """
        description_file = f"{tool_name}.md"

        try:
            template = self.env.get_template(description_file)
            # Render with limited context vars for optional schema embedding
            return cast(str, template.render(**self._context_vars))  # type: ignore[redundant-cast,unused-ignore]
        except Exception as e:
            # Surface a clearer message that includes Jinja include/search paths
            search_paths = "unknown"
            if self.env.loader and hasattr(self.env.loader, "searchpath"):
                search_paths = ", ".join(self.env.loader.searchpath)
            raise FileNotFoundError(
                f"Failed to load tool description '{description_file}'. Searched in: {search_paths}. "
                f"Original error: {e!s}"
            ) from e

    # duplicate clear_cache removed

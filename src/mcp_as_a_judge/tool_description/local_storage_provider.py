"""Tool description provider for loading descriptions from local markdown files."""

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
        self.env = Environment(
            loader=FileSystemLoader(str(descriptions_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # nosec B701 - Safe for description files (not HTML)  # noqa: S701
        )

        # Cache for loaded descriptions to avoid repeated file I/O
        self._description_cache: dict[str, str] = {}

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
            # Render without any variables (descriptions are static)
            return cast(str, template.render())  # type: ignore[redundant-cast,unused-ignore]
        except Exception as e:
            raise FileNotFoundError(
                f"Tool description file '{description_file}' not found in {self.descriptions_dir}"
            ) from e

    def clear_cache(self) -> None:
        """Clear the description cache.

        Useful for testing or when description files are updated at runtime.
        """
        self._description_cache.clear()

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names based on description files.

        Returns:
            List of tool names that have description files
        """
        if not self.descriptions_dir.exists():
            return []

        tool_names = []
        for file_path in self.descriptions_dir.glob("*.md"):
            tool_name = file_path.stem  # Remove .md extension
            tool_names.append(tool_name)

        return sorted(tool_names)

    @property
    def provider_type(self) -> str:
        """Return provider type identifier.

        Returns:
            String identifier for this provider type
        """
        return "local_storage"

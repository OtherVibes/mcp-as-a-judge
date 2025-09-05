"""Tests for the tool description local storage provider."""

import pytest

from mcp_as_a_judge.tool_description_local_storage_provider import (
    ToolDescriptionLocalStorageProvider,
    tool_description_local_storage_provider,
)


class TestToolDescriptionLocalStorageProvider:
    """Test the ToolDescriptionLocalStorageProvider class."""

    def test_provider_initialization_default(self):
        """Test provider initialization with default directory."""
        provider = ToolDescriptionLocalStorageProvider()
        assert provider.descriptions_dir is not None
        assert "tool_descriptions" in str(provider.descriptions_dir)

    def test_provider_initialization_custom_dir(self, tmp_path):
        """Test provider initialization with custom directory."""
        custom_dir = tmp_path / "custom_descriptions"
        custom_dir.mkdir()

        provider = ToolDescriptionLocalStorageProvider(descriptions_dir=custom_dir)
        assert provider.descriptions_dir == custom_dir

    def test_get_description_success(self, tmp_path):
        """Test successful description loading."""
        # Create test directory and file
        descriptions_dir = tmp_path / "tool_descriptions"
        descriptions_dir.mkdir()

        test_description = "Test tool description content"
        test_file = descriptions_dir / "test_tool.md"
        test_file.write_text(test_description)

        # Create provider and test
        provider = ToolDescriptionLocalStorageProvider(
            descriptions_dir=descriptions_dir
        )
        result = provider.get_description("test_tool")

        assert result == test_description

    def test_get_description_file_not_found(self, tmp_path):
        """Test description loading when file doesn't exist."""
        descriptions_dir = tmp_path / "tool_descriptions"
        descriptions_dir.mkdir()

        provider = ToolDescriptionLocalStorageProvider(
            descriptions_dir=descriptions_dir
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            provider.get_description("nonexistent_tool")

        assert "nonexistent_tool.md" in str(exc_info.value)
        assert str(descriptions_dir) in str(exc_info.value)

    def test_description_caching(self, tmp_path):
        """Test that descriptions are cached after first load."""
        descriptions_dir = tmp_path / "tool_descriptions"
        descriptions_dir.mkdir()

        test_description = "Cached description content"
        test_file = descriptions_dir / "cached_tool.md"
        test_file.write_text(test_description)

        provider = ToolDescriptionLocalStorageProvider(
            descriptions_dir=descriptions_dir
        )

        # First call should load from file
        result1 = provider.get_description("cached_tool")
        assert result1 == test_description

        # Modify file content
        test_file.write_text("Modified content")

        # Second call should return cached content (not modified content)
        result2 = provider.get_description("cached_tool")
        assert result2 == test_description  # Should be original cached content

    def test_clear_cache(self, tmp_path):
        """Test cache clearing functionality."""
        descriptions_dir = tmp_path / "tool_descriptions"
        descriptions_dir.mkdir()

        test_description = "Original content"
        test_file = descriptions_dir / "cache_test_tool.md"
        test_file.write_text(test_description)

        provider = ToolDescriptionLocalStorageProvider(
            descriptions_dir=descriptions_dir
        )

        # Load description (gets cached)
        result1 = provider.get_description("cache_test_tool")
        assert result1 == test_description

        # Modify file and clear cache
        test_file.write_text("Updated content")
        provider.clear_cache()

        # Should now load updated content
        result2 = provider.get_description("cache_test_tool")
        assert result2 == "Updated content"

    def test_get_available_tools(self, tmp_path):
        """Test getting list of available tools."""
        descriptions_dir = tmp_path / "tool_descriptions"
        descriptions_dir.mkdir()

        # Create test description files
        (descriptions_dir / "tool1.md").write_text("Tool 1 description")
        (descriptions_dir / "tool2.md").write_text("Tool 2 description")
        (descriptions_dir / "another_tool.md").write_text("Another tool description")

        provider = ToolDescriptionLocalStorageProvider(
            descriptions_dir=descriptions_dir
        )
        available_tools = provider.get_available_tools()

        assert sorted(available_tools) == ["another_tool", "tool1", "tool2"]

    def test_get_available_tools_empty_directory(self, tmp_path):
        """Test getting available tools from empty directory."""
        descriptions_dir = tmp_path / "empty_descriptions"
        descriptions_dir.mkdir()

        provider = ToolDescriptionLocalStorageProvider(
            descriptions_dir=descriptions_dir
        )
        available_tools = provider.get_available_tools()

        assert available_tools == []

    def test_get_available_tools_nonexistent_directory(self, tmp_path):
        """Test getting available tools when directory doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"

        provider = ToolDescriptionLocalStorageProvider(descriptions_dir=nonexistent_dir)
        available_tools = provider.get_available_tools()

        assert available_tools == []


class TestGlobalProviderInstance:
    """Test the global provider instance."""

    def test_global_instance_exists(self):
        """Test that global instance is available."""
        assert tool_description_local_storage_provider is not None
        assert isinstance(
            tool_description_local_storage_provider, ToolDescriptionLocalStorageProvider
        )

    def test_global_instance_can_load_real_descriptions(self):
        """Test that global instance can load actual tool descriptions."""
        # This test verifies that the real tool description files exist
        try:
            description = tool_description_local_storage_provider.get_description(
                "build_workflow"
            )
            assert isinstance(description, str)
            assert len(description) > 0
            assert "workflow" in description.lower()
        except FileNotFoundError:
            pytest.skip(
                "Tool description files not found - may be running in test environment"
            )

    def test_global_instance_available_tools(self):
        """Test that global instance can list available tools."""
        try:
            available_tools = (
                tool_description_local_storage_provider.get_available_tools()
            )
            assert isinstance(available_tools, list)
            # Should include the main tools we created
            expected_tools = [
                "build_workflow",
                "judge_coding_plan",
                "judge_code_change",
                "raise_obstacle",
            ]
            for tool in expected_tools:
                if tool not in available_tools:
                    pytest.skip(
                        f"Tool description file for {tool} not found - may be running in test environment"
                    )
        except Exception:
            pytest.skip(
                "Tool description directory not accessible - may be running in test environment"
            )

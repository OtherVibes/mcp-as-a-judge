"""Integration tests for tool description provider factory with server."""

import pytest

from mcp_as_a_judge.tool_description.factory import (
    tool_description_provider,
    tool_description_provider_factory,
)
from mcp_as_a_judge.tool_description.interface import ToolDescriptionProvider
from mcp_as_a_judge.tool_description.local_storage_provider import LocalStorageProvider


class TestToolDescriptionIntegration:
    """Test integration between factory and server."""

    def test_server_can_import_provider(self):
        """Test that server can import the tool description provider."""
        # This test verifies the import path works
        assert tool_description_provider is not None
        assert isinstance(tool_description_provider, ToolDescriptionProvider)
        assert isinstance(tool_description_provider, LocalStorageProvider)

    def test_server_can_import_factory(self):
        """Test that server can import the tool description factory."""
        assert tool_description_provider_factory is not None

        # Test that factory can create providers
        provider = tool_description_provider_factory.create_provider()
        assert isinstance(provider, ToolDescriptionProvider)

    def test_provider_consistency(self):
        """Test that factory and direct import return same type."""
        factory_provider = tool_description_provider_factory.create_provider()
        direct_provider = tool_description_provider

        # Both should be the same type
        assert type(factory_provider) is type(direct_provider)
        assert factory_provider.provider_type == direct_provider.provider_type

    def test_server_import_works(self):
        """Test that server can be imported without errors."""
        try:
            # This should not raise any import errors
            from mcp_as_a_judge.server import mcp

            assert mcp is not None
            assert mcp.name == "MCP-as-a-Judge"
        except ImportError as e:
            pytest.fail(f"Server import failed: {e}")

    def test_tool_descriptions_accessible(self):
        """Test that tool descriptions are accessible through the provider."""
        try:
            # Test that we can get descriptions for known tools
            description = tool_description_provider.get_description("set_coding_task")
            assert isinstance(description, str)
            assert len(description) > 0
        except FileNotFoundError:
            pytest.skip(
                "Tool description files not found - may be running in test environment"
            )

    def test_factory_extensibility_design(self):
        """Test that factory is designed for future extensibility."""
        # Verify factory methods exist and work
        assert hasattr(tool_description_provider_factory, "create_provider")
        assert hasattr(tool_description_provider_factory, "get_available_providers")

        # Test provider info
        providers_info = tool_description_provider_factory.get_available_providers()
        assert isinstance(providers_info, dict)
        assert "local_storage" in providers_info
        assert providers_info["local_storage"]["available"] is True

    def test_backward_compatibility(self):
        """Test that the new factory maintains backward compatibility."""
        # The global tool_description_provider should work the same as before
        assert hasattr(tool_description_provider, "get_description")
        assert hasattr(tool_description_provider, "get_available_tools")
        assert hasattr(tool_description_provider, "clear_cache")

        # Test that methods are callable
        assert callable(tool_description_provider.get_description)
        assert callable(tool_description_provider.get_available_tools)
        assert callable(tool_description_provider.clear_cache)

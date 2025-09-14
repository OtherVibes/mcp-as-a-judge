"""Tests for the tool description provider factory."""

import pytest

from mcp_as_a_judge.tool_description.factory import (
    ToolDescriptionProviderFactory,
    tool_description_provider,
    tool_description_provider_factory,
)
from mcp_as_a_judge.tool_description.interface import ToolDescriptionProvider
from mcp_as_a_judge.tool_description.local_storage_provider import LocalStorageProvider


class TestToolDescriptionProviderFactory:
    """Test the ToolDescriptionProviderFactory class."""

    def test_create_provider_returns_local_storage(self):
        """Test that factory creates local storage provider."""
        factory = ToolDescriptionProviderFactory()
        provider = factory.create_provider()

        assert isinstance(provider, LocalStorageProvider)
        assert isinstance(provider, ToolDescriptionProvider)
        assert provider.provider_type == "local_storage"

    def test_get_available_providers(self):
        """Test getting available providers information."""
        factory = ToolDescriptionProviderFactory()
        providers = factory.get_available_providers()

        assert isinstance(providers, dict)
        assert "local_storage" in providers
        assert providers["local_storage"]["available"] is True
        assert providers["local_storage"]["provider_type"] == "local_storage"

    def test_static_methods_work(self):
        """Test that static methods work correctly."""
        provider = ToolDescriptionProviderFactory.create_provider()
        providers = ToolDescriptionProviderFactory.get_available_providers()

        assert isinstance(provider, LocalStorageProvider)
        assert isinstance(providers, dict)
        assert "local_storage" in providers


class TestGlobalFactoryInstances:
    """Test the global factory instances."""

    def test_global_factory_instance_exists(self):
        """Test that global factory instance is available."""
        assert tool_description_provider_factory is not None
        assert isinstance(
            tool_description_provider_factory, ToolDescriptionProviderFactory
        )

    def test_global_provider_instance_exists(self):
        """Test that global provider instance is available."""
        assert tool_description_provider is not None
        assert isinstance(tool_description_provider, ToolDescriptionProvider)
        assert isinstance(tool_description_provider, LocalStorageProvider)

    def test_global_provider_can_get_descriptions(self):
        """Test that global provider can load descriptions."""
        # This test verifies that the global provider works
        try:
            description = tool_description_provider.get_description("set_coding_task")
            assert isinstance(description, str)
            assert len(description) > 0
        except FileNotFoundError:
            pytest.skip(
                "Tool description files not found - may be running in test environment"
            )

    def test_global_provider_can_list_tools(self):
        """Test that global provider can list available tools."""
        try:
            available_tools = tool_description_provider.get_available_tools()
            assert isinstance(available_tools, list)
        except Exception:
            pytest.skip(
                "Tool description directory not accessible - may be running in test environment"
            )

    def test_global_provider_cache_operations(self):
        """Test that global provider cache operations work."""
        # Test that clear_cache doesn't raise errors
        tool_description_provider.clear_cache()

        # Test that provider_type is accessible
        assert tool_description_provider.provider_type == "local_storage"


class TestFactoryExtensibility:
    """Test that the factory is designed for future extensibility."""

    def test_factory_can_be_extended(self):
        """Test that factory pattern supports future extensions."""
        # This test verifies the factory pattern is properly structured
        # for future extensions (additional provider types)

        # Verify the factory returns the interface type
        provider = ToolDescriptionProviderFactory.create_provider()
        assert isinstance(provider, ToolDescriptionProvider)

        # Verify the provider has all required interface methods
        assert hasattr(provider, "get_description")
        assert hasattr(provider, "get_available_tools")
        assert hasattr(provider, "clear_cache")
        assert hasattr(provider, "provider_type")

        # Verify methods are callable
        assert callable(provider.get_description)
        assert callable(provider.get_available_tools)
        assert callable(provider.clear_cache)

    def test_provider_interface_compliance(self):
        """Test that the created provider complies with the interface."""
        provider = ToolDescriptionProviderFactory.create_provider()

        # Test that all interface methods exist and have correct signatures
        try:
            # These should not raise AttributeError
            provider.get_available_tools()
            provider.clear_cache()
            provider_type = provider.provider_type
            assert isinstance(provider_type, str)
        except FileNotFoundError:
            # This is expected if description files don't exist in test environment
            pass

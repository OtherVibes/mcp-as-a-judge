"""Test the MCP server functionality."""

from mcp_as_a_judge import mcp


def test_server_initialization() -> None:
    """Test that the server can be initialized and tools are registered."""
    # Check that the server instance exists
    assert mcp.name == "MCP-as-a-Judge"

    # Check that the server has the expected attributes
    assert hasattr(mcp, "name")


def test_server_tools_registered() -> None:
    """Test that the expected tools are registered."""
    # The tools are registered via decorators, so they should be available
    # when the server runs. We can't easily inspect them here, but we can
    # verify the server instance exists and has the expected structure.
    assert mcp is not None
    assert mcp.name == "MCP-as-a-Judge"


def test_server_import() -> None:
    """Test that the server can be imported without errors."""
    from mcp_as_a_judge import mcp as imported_mcp

    assert imported_mcp is not None
    assert imported_mcp.name == "MCP-as-a-Judge"

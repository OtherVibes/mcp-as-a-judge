"""
Cloudflare Python Worker for MCP as a Judge

This worker reuses your existing MCP server with Durable Objects.
Follows the official Cloudflare MCP pattern.
"""

from workers import DurableObject, WorkerEntrypoint

# Import your existing MCP server
from mcp_as_a_judge.server import mcp


class FastMCPServer(DurableObject):
    """MCP as a Judge server using Cloudflare Durable Objects."""

    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        # Use streamable_http_app() instead of sse_app() for better compatibility
        self.app = mcp.streamable_http_app()

    async def fetch(self, request):
        """Handle all MCP requests through your existing server."""
        return await self.app(request)


class Default(WorkerEntrypoint):
    """Cloudflare Worker entry point that routes to Durable Object."""

    async def fetch(self, request):
        """Route requests to the MCP Durable Object."""
        # Get the Durable Object instance
        id = self.env.MCP_OBJECT.idFromName("mcp-as-a-judge")
        stub = self.env.MCP_OBJECT.get(id)

        # Forward the request to the Durable Object
        return await stub.fetch(request)



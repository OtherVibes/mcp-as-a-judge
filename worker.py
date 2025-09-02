"""
Cloudflare Python Workers entry point for MCP as a Judge.

This file serves as the main entry point for the Python Worker,
following the official Cloudflare Python Workers patterns.
"""

from workers import DurableObject, WorkerEntrypoint


class FastMCPServer(DurableObject):
    """Durable Object that hosts the MCP server instance."""
    
    def __init__(self, ctx, env):
        self.ctx = ctx
        self.env = env
        
        # Import and initialize the MCP server
        from src.mcp_as_a_judge.server import mcp
        self.app = mcp.streamable_http_app()

    async def call(self, request):
        """Handle requests to the MCP server."""
        import asgi
        return await asgi.fetch(self.app, request, self.env, self.ctx)


class Default(WorkerEntrypoint):
    """Main entry point for the Python Worker."""
    
    async def fetch(self, request):
        """Handle incoming HTTP requests."""
        # Generate a unique ID for the MCP server instance
        # Using a consistent name for the MCP server
        id = self.env.ns.idFromName("mcp-as-a-judge")
        obj = self.env.ns.get(id)
        return await obj.call(request)

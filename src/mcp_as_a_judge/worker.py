from workers import DurableObject, WorkerEntrypoint


class FastMCPServer(DurableObject):
    def __init__(self, ctx, env):
        self.ctx = ctx
        self.env = env
        from mcp_as_a_judge.server import mcp

        self.app = mcp.streamable_http_app()

    async def call(self, request):
        import asgi
        return await asgi.fetch(self.app, request, self.env, self.ctx)



class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # Generate a unique ID for the MCP server instance
        # Using a consistent name for the MCP server
        id = self.env.ns.idFromName("mcp-as-a-judge")
        obj = self.env.ns.get(id)
        return await obj.call(request)
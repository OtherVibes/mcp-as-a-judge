from workers import DurableObject


class FastMCPServer(DurableObject):
    def __init__(self, ctx, env):
        self.ctx = ctx
        self.env = env
        from mcp_as_a_judge.server import mcp

        self.app = mcp.streamable_http_app()

    async def call(self, request):
        import asgi
        return await asgi.fetch(self.app, request, self.env, self.ctx)



async def on_fetch(request, env):
    id = env.ns.idFromName("mcp-as-a-judge")
    obj = env.ns.get(id)
    return await obj.call(request)
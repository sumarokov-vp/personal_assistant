from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp_types import CallToolRequestParams, TextContent

from workers.mcp.project.project_parameter import PROJECT_ARGUMENT
from workers.mcp.project.project_resolution import PROJECT_RESOLUTION_STATE_KEY
from workers.mcp.project.project_resolver import ProjectResolver

PROJECT_HEADER = "x-project"


class ProjectGate(Middleware):
    def __init__(self, resolver: ProjectResolver) -> None:
        self._resolver = resolver

    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        arguments = context.message.arguments or {}
        resolution = self._resolver.resolve(
            header=get_http_headers().get(PROJECT_HEADER),
            argument=arguments.get(PROJECT_ARGUMENT),
        )
        if context.fastmcp_context is not None:
            await context.fastmcp_context.set_state(
                PROJECT_RESOLUTION_STATE_KEY, resolution, serializable=False
            )
        if not resolution.allowed:
            return ToolResult(
                content=[TextContent(text=f"Проект не разрешён: {resolution.project}")],
                is_error=True,
            )
        return await call_next(context)

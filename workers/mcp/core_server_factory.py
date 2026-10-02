from collections.abc import Sequence

from ai_framework import BaseTool
from fastmcp import FastMCP
from fastmcp.server.auth import AuthProvider
from fastmcp.server.middleware import Middleware
from starlette.applications import Starlette

from workers.mcp.base_tool_adapter import BaseToolAdapter

SERVER_NAME = "assistant-core"
MCP_PATH = "/mcp"


def build_core_server(
    tools: Sequence[BaseTool],
    auth: AuthProvider,
    middleware: Sequence[Middleware] = (),
) -> FastMCP:
    return FastMCP(
        name=SERVER_NAME,
        auth=auth,
        middleware=middleware,
        tools=[BaseToolAdapter.of(tool) for tool in tools],
        mask_error_details=False,
    )


def build_core_app(server: FastMCP) -> Starlette:
    return server.http_app(path=MCP_PATH, transport="streamable-http")

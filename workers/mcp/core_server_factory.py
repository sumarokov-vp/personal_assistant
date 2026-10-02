from collections.abc import Sequence, Set

from ai_framework import BaseTool
from fastmcp import FastMCP
from fastmcp.server.auth import AuthProvider
from fastmcp.server.middleware import Middleware
from starlette.applications import Starlette

from workers.mcp.base_tool_adapter import BaseToolAdapter
from workers.mcp.journal.protocols.i_journal_sink import IJournalSink
from workers.mcp.journal.request_journal import RequestJournal
from workers.mcp.project.project_gate import ProjectGate
from workers.mcp.project.project_parameter import with_project_parameter
from workers.mcp.project.project_resolver import ProjectResolver

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
        tools=[
            BaseToolAdapter.of(
                tool, parameters=with_project_parameter(tool.input_schema)
            )
            for tool in tools
        ],
        mask_error_details=False,
    )


def build_core_middleware(
    journal: IJournalSink, allowed_projects: Set[str]
) -> list[Middleware]:
    return [RequestJournal(journal), ProjectGate(ProjectResolver(allowed_projects))]


def build_core_app(server: FastMCP) -> Starlette:
    return server.http_app(path=MCP_PATH, transport="streamable-http")

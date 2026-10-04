import json
from typing import Any

from fastmcp.server.context import Context
from fastmcp.server.dependencies import get_access_token, get_http_headers
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from pydantic import BaseModel

from workers.mcp.journal.journal_entry import JournalEntry, Outcome
from workers.mcp.journal.protocols.i_journal_sink import IJournalSink
from workers.mcp.journal.secret_headers import mask_secret_headers
from workers.mcp.project.project_resolution import (
    PROJECT_RESOLUTION_STATE_KEY,
    ProjectResolution,
)

TOOL_CALL_METHOD = "tools/call"
EMAIL_CLAIM = "email"


class RequestJournal(Middleware):
    def __init__(self, sink: IJournalSink) -> None:
        self._sink = sink

    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        result: Any = None
        completed = False
        try:
            result = await call_next(context)
            completed = True
        finally:
            await self._record(context, result, completed)
        return result

    async def _record(
        self, context: MiddlewareContext[Any], result: Any, completed: bool
    ) -> None:
        resolution = await _project_resolution(context)
        entry = JournalEntry(
            time=context.timestamp,
            method=context.method,
            client=_client_info(context),
            headers=mask_secret_headers(get_http_headers(include_all=True)),
            meta=_request_meta(context.fastmcp_context),
            tool=_tool_name(context),
            project=resolution.project if resolution else None,
            project_source=resolution.source if resolution else None,
            user=_user_email(),
            outcome=_outcome(result, completed, resolution),
        )
        self._sink.append(
            json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, default=str)
        )


def _params(message: Any) -> Any:
    return getattr(message, "params", message)


def _tool_name(context: MiddlewareContext[Any]) -> str | None:
    if context.method != TOOL_CALL_METHOD:
        return None
    name = getattr(_params(context.message), "name", None)
    return name if isinstance(name, str) else None


def _client_info(context: MiddlewareContext[Any]) -> dict[str, Any] | None:
    info = getattr(_params(context.message), "client_info", None)
    fastmcp_context = context.fastmcp_context
    if info is None and fastmcp_context is not None:
        request_context = fastmcp_context.request_context
        if request_context is not None:
            client_params = request_context.session.client_params
            info = client_params.client_info if client_params else None
    return (
        info.model_dump(mode="json", exclude_none=True)
        if isinstance(info, BaseModel)
        else None
    )


def _request_meta(fastmcp_context: Context | None) -> dict[str, Any] | None:
    if fastmcp_context is None or fastmcp_context.request_context is None:
        return None
    meta = fastmcp_context.request_context.meta
    return dict(meta) if meta else None


async def _project_resolution(
    context: MiddlewareContext[Any],
) -> ProjectResolution | None:
    if context.method != TOOL_CALL_METHOD or context.fastmcp_context is None:
        return None
    resolution = await context.fastmcp_context.get_state(PROJECT_RESOLUTION_STATE_KEY)
    return resolution if isinstance(resolution, ProjectResolution) else None


def _outcome(
    result: Any, completed: bool, resolution: ProjectResolution | None
) -> Outcome:
    if resolution is not None and not resolution.allowed:
        return "denied"
    if not completed or (isinstance(result, ToolResult) and result.is_error):
        return "error"
    return "ok"


def _user_email() -> str | None:
    access_token = get_access_token()
    email = access_token.claims.get(EMAIL_CLAIM) if access_token else None
    return email if isinstance(email, str) else None

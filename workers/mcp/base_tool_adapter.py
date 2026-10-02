from typing import Any, Self

from ai_framework import BaseTool, ToolContext
from anyio import to_thread
from fastmcp.exceptions import ToolError
from fastmcp.tools import Tool, ToolResult
from pydantic import BaseModel, PrivateAttr, ValidationError

from workers.mcp.tool_output_content import to_content_blocks


class BaseToolAdapter(Tool):
    _base_tool: BaseTool = PrivateAttr()

    @classmethod
    def of(cls, base_tool: BaseTool, parameters: dict[str, Any] | None = None) -> Self:
        adapter = cls(
            name=base_tool.name,
            description=base_tool.description,
            parameters=parameters if parameters is not None else base_tool.input_schema,
        )
        adapter._base_tool = base_tool
        return adapter

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        output = await to_thread.run_sync(self._execute, arguments)
        return ToolResult(content=to_content_blocks(output))

    def _execute(self, arguments: dict[str, Any]) -> object:
        base_tool = self._base_tool
        return base_tool.execute(self._input(arguments), ToolContext())

    def _input(self, arguments: dict[str, Any]) -> BaseModel:
        try:
            return self._base_tool.Input(**arguments)
        except ValidationError as error:
            raise ToolError(f"Tool {self.name} failed: {error}") from error

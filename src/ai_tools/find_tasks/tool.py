import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.find_tasks.protocols.i_task_finder import ITaskFinder


class FindTasksInput(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=50, ge=1, le=200)


class FindTasksTool(BaseTool):
    name: ClassVar[str] = "find_tasks"
    description: ClassVar[str] = (
        "Ищет активные задачи Todoist владельца по фильтру Todoist. "
        "query — выражение фильтра в синтаксисе Todoist, передаётся как есть: "
        "«today | overdue» — на сегодня и просроченные, «7 days» — на неделю вперёд, "
        "«search: ЭЦП» — по тексту, «@pa» — поставленные ассистентом, «#Входящие» — по проекту, "
        "«no date» — без срока; условия связываются через & и |. "
        "limit — сколько задач вернуть максимум. "
        "Возвращает tasks (id, content, description, due, labels, project, url) и count."
    )

    Input: ClassVar[type[BaseModel]] = FindTasksInput

    def __init__(self, finder: ITaskFinder) -> None:
        self._finder = finder

    def execute(self, input: FindTasksInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        cards = self._finder.find(query=input.query, limit=input.limit)
        return json.dumps(
            {
                "tasks": [card.model_dump(mode="json") for card in cards],
                "count": len(cards),
            },
            ensure_ascii=False,
        )

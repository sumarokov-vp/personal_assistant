from datetime import date
from typing import ClassVar, Self

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.ai_tools.update_task.protocols.i_task_updater import ITaskUpdater

CLEARED_DUE = "no date"


class UpdateTaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_id: str = Field(min_length=1)
    due: str | None = None
    clear_due: bool = False
    deadline: date | None = None
    clear_deadline: bool = False
    add_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_changes(self) -> Self:
        if self.due and self.clear_due:
            raise ValueError("due и clear_due вместе не передаются")
        if self.deadline and self.clear_deadline:
            raise ValueError("deadline и clear_deadline вместе не передаются")
        if not (
            self.due
            or self.clear_due
            or self.deadline
            or self.clear_deadline
            or any(self.add_labels)
        ):
            raise ValueError("Нечего менять: передай срок, дедлайн или метки")
        return self


class UpdateTaskTool(BaseTool):
    name: ClassVar[str] = "update_task"
    description: ClassVar[str] = (
        "Меняет у задачи Todoist только срок, дедлайн и метки — на любой задаче владельца. "
        "task_id — id задачи. "
        "due — новый срок (когда владелец займётся): дата «2026-10-01», дата и время или "
        "фраза Todoist («в пятницу»). clear_due=true — снять срок. "
        "deadline — новый дедлайн, жёсткая внешняя граница, дата YYYY-MM-DD; "
        "clear_deadline=true — снять дедлайн. Срок и дедлайн — разные поля. "
        "add_labels — метки, которые дописать к текущим; только названные владельцем, "
        "pa сюда не передавай. Незаданное поле не меняется. "
        "Название, описание, проект, закрытие и удаление этот инструмент не трогает. "
        "Возвращает задачу после правки: id, content, description, due, deadline, "
        "parent_id, labels, project, url."
    )

    Input: ClassVar[type[BaseModel]] = UpdateTaskInput

    def __init__(self, updater: ITaskUpdater) -> None:
        self._updater = updater

    def execute(self, input: UpdateTaskInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        card = self._updater.update_task(
            task_id=input.task_id,
            due=CLEARED_DUE if input.clear_due else input.due or None,
            deadline=input.deadline.isoformat() if input.deadline else None,
            clear_deadline=input.clear_deadline,
            labels=[label for label in input.add_labels if label] or None,
        )
        return card.model_dump_json()

import json
from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.case_open.protocols.i_case_opener import ICaseOpener
from src.cases.errors.cases_service_error import CasesServiceError


class CaseOpenInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        min_length=1, description="Короткое имя темы: «Новая компания (ТОО)»"
    )
    summary: str = Field(
        min_length=1,
        description="Что за тема и зачем она владельцу — одним-двумя предложениями",
    )


class CaseOpenTool(BaseTool):
    name: ClassVar[str] = "case_open"
    description: ClassVar[str] = (
        "Заводит новый кейс — тему или линию жизни владельца, у которой будет продолжение. "
        "Не задачу: задачи и шаги живут внутри кейса. Перед заведением проверь case_find, "
        "что такой темы ещё нет. Возвращает case_id."
    )
    Input: ClassVar[type[BaseModel]] = CaseOpenInput

    def __init__(self, opener: ICaseOpener) -> None:
        self._opener = opener

    def execute(self, input: CaseOpenInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        try:
            case = self._opener.create_case(title=input.title, summary=input.summary)
        except CasesServiceError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return f"Кейс заведён: {case.id} · {case.title}"

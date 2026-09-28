import json
from typing import ClassVar, Literal

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.case_update.protocols.i_case_updater import ICaseUpdater
from src.cases.errors.cases_service_error import CasesServiceError
from src.cases.models.case_update import CaseUpdate


class CaseUpdateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    case_id: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, min_length=1)
    status: Literal["open", "closed"] | None = Field(
        default=None, description="closed — тема завершена; open — вернуть в работу"
    )


class CaseUpdateTool(BaseTool):
    name: ClassVar[str] = "case_update"
    description: ClassVar[str] = (
        "Меняет у кейса название, описание (что за тема и зачем) или статус "
        "(closed — тема завершена, open — снова в работе). Передавай только то, что меняешь."
    )
    Input: ClassVar[type[BaseModel]] = CaseUpdateInput

    def __init__(self, updater: ICaseUpdater) -> None:
        self._updater = updater

    def execute(self, input: CaseUpdateInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        update = CaseUpdate.model_validate(
            input.model_dump(include={"title", "summary", "status"}, exclude_none=True)
        )
        if not update.model_fields_set:
            return json.dumps(
                {"error": "Нечего менять: передай title, summary или status."},
                ensure_ascii=False,
            )
        try:
            case = self._updater.update_case(input.case_id, update)
        except CasesServiceError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return f"Кейс обновлён: {case.id} · {case.status} · {case.title}"

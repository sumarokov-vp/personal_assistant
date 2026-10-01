import json
from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.schedule_cancel.protocols.i_schedule_canceller import (
    IScheduleCanceller,
)
from src.scheduler.errors.scheduler_service_error import SchedulerServiceError


class ScheduleCancelInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    schedule_id: str = Field(min_length=1, description="id расписания из schedule_list")


class ScheduleCancelTool(BaseTool):
    name: ClassVar[str] = "schedule_cancel"
    description: ClassVar[str] = (
        "Отменяет расписание: больше оно не сработает. Отмена ложится событием в ленту "
        "кейса. id — из schedule_list."
    )
    Input: ClassVar[type[BaseModel]] = ScheduleCancelInput

    def __init__(self, canceller: IScheduleCanceller) -> None:
        self._canceller = canceller

    def execute(self, input: ScheduleCancelInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        try:
            schedule = self._canceller.cancel_schedule(input.schedule_id)
        except SchedulerServiceError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return f"Расписание отменено: {schedule.id} · {schedule.instruction}"

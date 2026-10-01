import json
from typing import ClassVar
from zoneinfo import ZoneInfo

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.schedule_common.schedule_moments import (
    owner_moment,
    periodicity,
    upcoming_moments,
)
from src.ai_tools.schedule_list.protocols.i_case_finder import ICaseFinder
from src.ai_tools.schedule_list.protocols.i_schedule_lister import IScheduleLister
from src.cases.errors.cases_service_error import CasesServiceError
from src.scheduler.errors.scheduler_service_error import SchedulerServiceError
from src.scheduler.models.schedule import Schedule
from src.scheduler.models.schedule_query import ScheduleQuery, ScheduleStatusFilter

CASE_TITLES_LIMIT = 100


class ScheduleListInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    case_id: str | None = Field(
        default=None, description="Только расписания этого кейса"
    )
    status: ScheduleStatusFilter = Field(
        default="live",
        description="live — действующие (по умолчанию: active и paused), active, "
        "paused, done — выполненные разовые, cancelled — отменённые, all — все",
    )


class ScheduleListTool(BaseTool):
    name: ClassVar[str] = "schedule_list"
    description: ClassVar[str] = (
        "Показывает расписания владельца строками «id · когда · кейс · инструкция», "
        "ближайшие первыми; время — в поясе владельца. По умолчанию только действующие."
    )
    Input: ClassVar[type[BaseModel]] = ScheduleListInput

    def __init__(
        self,
        lister: IScheduleLister,
        timezone: ZoneInfo,
        cases: ICaseFinder | None = None,
    ) -> None:
        self._lister = lister
        self._timezone = timezone
        self._cases = cases

    def execute(self, input: ScheduleListInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        query = ScheduleQuery(status=input.status, case_id=input.case_id or None)
        try:
            schedules = self._lister.list_schedules(query)
        except SchedulerServiceError as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        if not schedules:
            return "Расписаний не найдено."
        titles = self._case_titles()
        lines = [self._line(schedule, titles) for schedule in schedules]
        return f"Расписаний: {len(schedules)}\n" + "\n".join(lines)

    def _case_titles(self) -> dict[str, str]:
        if self._cases is None:
            return {}
        try:
            cases = self._cases.find_cases(
                query=None, status="all", limit=CASE_TITLES_LIMIT
            )
        except CasesServiceError:
            return {}
        return {case.id: case.title for case in cases}

    def _line(self, schedule: Schedule, titles: dict[str, str]) -> str:
        case = titles.get(schedule.case_id, schedule.case_id)
        parts = [schedule.id, self._when(schedule), case, schedule.instruction]
        if schedule.status != "active":
            parts.insert(1, schedule.status)
        return " · ".join(parts)

    def _when(self, schedule: Schedule) -> str:
        moments = upcoming_moments(schedule, self._timezone)
        if schedule.kind == "periodic":
            nearest = f", ближайшее {moments[0]}" if moments else ""
            return f"{periodicity(schedule)}{nearest}"
        moment = schedule.run_at or schedule.next_run_at
        return owner_moment(moment, self._timezone) if moment else "без времени"

import json
from datetime import datetime
from typing import ClassVar
from zoneinfo import ZoneInfo, available_timezones

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, ConfigDict, Field

from src.ai_tools.schedule_add.protocols.i_schedule_creator import IScheduleCreator
from src.ai_tools.schedule_common.schedule_moments import (
    periodicity,
    upcoming_moments,
)
from src.scheduler.errors.scheduler_service_error import SchedulerServiceError
from src.scheduler.models.new_schedule import NewSchedule
from src.scheduler.models.schedule import Schedule


class ScheduleAddInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    case_id: str = Field(
        min_length=1,
        description="Кейс, к которому относится расписание: case_id из case_find. Темы "
        "нет — inbox (служебный кейс «Без темы»)",
    )
    instruction: str = Field(
        min_length=1,
        description="Что сделать в назначенное время — так, чтобы было понятно без "
        "этого разговора: «Проверь почту и ленту кейса: ответил ли нотариус по "
        "регистрации ТОО»",
    )
    at: datetime | None = Field(
        default=None,
        description="Разовый запуск: YYYY-MM-DDTHH:MM, без пояса — пояс владельца. "
        "Ровно одно из at и cron",
    )
    cron: str | None = Field(
        default=None,
        description="Периодический запуск: 5 полей «минута час день месяц день_недели» "
        "(0 — воскресенье); «1#1» в дне недели — первый понедельник месяца. Ровно "
        "одно из at и cron",
    )
    timezone: str | None = Field(
        default=None,
        description="Пояс IANA (Asia/Almaty). Не передан — пояс владельца",
    )


class ScheduleAddTool(BaseTool):
    name: ClassVar[str] = "schedule_add"
    description: ClassVar[str] = (
        "Заводит запуск ассистента по расписанию, привязанный к кейсу: разовый (at) или "
        "периодический (cron). В назначенное время ассистент сам выполнит инструкцию с "
        "контекстом кейса и пришлёт владельцу результат. Возвращает id расписания и "
        "ближайшие срабатывания в поясе владельца."
    )
    Input: ClassVar[type[BaseModel]] = ScheduleAddInput

    def __init__(self, creator: IScheduleCreator, timezone: ZoneInfo) -> None:
        self._creator = creator
        self._timezone = timezone

    def execute(self, input: ScheduleAddInput, context: ToolContext) -> str:  # noqa: A002, ARG002
        if (input.at is None) == (input.cron is None):
            return _error(
                "Нужно ровно одно из двух: at (разово) или cron (периодически)."
            )
        timezone_name = input.timezone or self._timezone.key
        if timezone_name not in available_timezones():
            return _error(
                f"Неизвестный пояс «{timezone_name}»: нужен IANA, Asia/Almaty."
            )
        new_schedule = NewSchedule(
            case_id=input.case_id,
            instruction=input.instruction,
            at=_aware(input.at, ZoneInfo(timezone_name)),
            cron=input.cron or None,
            timezone=timezone_name,
        )
        try:
            schedule = self._creator.create_schedule(new_schedule)
        except SchedulerServiceError as error:
            return _error(str(error))
        return self._report(schedule)

    def _report(self, schedule: Schedule) -> str:
        moments = upcoming_moments(schedule, self._timezone)
        if schedule.kind == "once":
            when = moments[0] if moments else "время не вернулось"
            return (
                f"Расписание заведено: {schedule.id} · разово\n"
                f"Сработает ({self._timezone.key}): {when}"
            )
        nearest = (
            "; ".join(moments)
            or "сервис не вернул ближайших — дат владельцу не называй"
        )
        return (
            f"Расписание заведено: {schedule.id} · {periodicity(schedule)}\n"
            f"Ближайшие ({self._timezone.key}): {nearest}"
        )


def _aware(moment: datetime | None, timezone: ZoneInfo) -> datetime | None:
    if moment is None or moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=timezone)


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)

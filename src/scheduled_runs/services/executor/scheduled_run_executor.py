from datetime import datetime
from logging import getLogger
from zoneinfo import ZoneInfo

from src.scheduled_runs.services.entities.due_outcome import DueOutcome
from src.scheduled_runs.services.entities.incoming_due import IncomingDue
from src.scheduled_runs.services.entities.schedule_due import ScheduleDue
from src.scheduled_runs.services.executor.case_brief import CaseBrief
from src.scheduled_runs.services.executor.protocols.i_case_briefing import (
    ICaseBriefing,
)
from src.scheduled_runs.services.executor.protocols.i_due_parser import IDueParser
from src.scheduled_runs.services.executor.protocols.i_owner_notifier import (
    IOwnerNotifier,
)
from src.scheduled_runs.services.executor.protocols.i_run_journal import IRunJournal
from src.scheduled_runs.services.executor.protocols.i_run_model import IRunModel

logger = getLogger(__name__)

SCHEDULE_DUE_TYPE = "schedule.due"
EMPTY_ANSWER = "(модель не дала ответа)"
MOMENT_FORMAT = "%d.%m.%Y %H:%M"


class ScheduledRunExecutor:
    def __init__(
        self,
        scheduler_account: str,
        parser: IDueParser,
        journal: IRunJournal,
        briefing: ICaseBriefing,
        model: IRunModel,
        notifier: IOwnerNotifier,
    ) -> None:
        self._scheduler_account = scheduler_account
        self._parser = parser
        self._journal = journal
        self._briefing = briefing
        self._model = model
        self._notifier = notifier

    def handle(self, incoming: IncomingDue) -> DueOutcome:
        due = self._accepted(incoming)
        if due is None:
            return DueOutcome.REJECTED

        run = self._journal.start(due.run_id, due.schedule_id, due.case_id)
        if run.delivered_at is not None:
            logger.info("Scheduled run %s already delivered, skipped", due.run_id)
            return DueOutcome.ALREADY_DELIVERED

        brief = self._briefing.brief(due.case_id)
        reply = self._model.answer(due.thread_id, _request(due, brief))
        self._journal.finish(due.run_id, reply.error)
        if reply.error is not None:
            logger.warning("Scheduled run %s failed: %s", due.run_id, reply.error)
            self._notifier.notify(_failure_text(due, brief, reply.error))
        else:
            self._notifier.notify(_answer_text(due, brief, reply.text))
        self._journal.mark_delivered(due.run_id)
        logger.info("Scheduled run %s of %s delivered", due.run_id, due.schedule_id)
        return DueOutcome.DELIVERED

    def _accepted(self, incoming: IncomingDue) -> ScheduleDue | None:
        if incoming.sender != self._scheduler_account:
            logger.warning(
                "Schedule due rejected: user_id=%r is not %r",
                incoming.sender,
                self._scheduler_account,
            )
            return None
        if incoming.message_type != SCHEDULE_DUE_TYPE or not incoming.message_id:
            logger.warning(
                "Schedule due rejected: type=%r message_id=%r",
                incoming.message_type,
                incoming.message_id,
            )
            return None
        due = self._parser.parse(incoming.body)
        if due is None:
            return None
        if due.run_id != incoming.message_id:
            logger.warning(
                "Schedule due rejected: message_id=%r differs from run_id=%r",
                incoming.message_id,
                due.run_id,
            )
            return None
        return due


def _request(due: ScheduleDue, brief: CaseBrief) -> str:
    zone = due.zone
    lines = [
        f"Запуск по расписанию {due.run_id} (расписание {due.schedule_id}, "
        f"{_kind(due)}). Владельца в разговоре нет.",
        f"Срабатывание назначено на {_moment(due.scheduled_for, zone)} ({zone.key}), "
        f"выполняется {_moment(due.fired_at, zone)}{_late_note(due)}.",
        f"Инструкция владельца: {due.instruction}",
    ]
    if due.task_event_id:
        lines.append(f"Задача кейса: {due.task_event_id}")
    lines.append(f"Кейс {due.case_id}:")
    lines.append(brief.text)
    return "\n".join(lines)


def _answer_text(due: ScheduleDue, brief: CaseBrief, answer: str | None) -> str:
    body = answer if answer and answer.strip() else EMPTY_ANSWER
    return f"По расписанию · {_title(due, brief)}{_late_suffix(due)}:\n{body}"


def _failure_text(due: ScheduleDue, brief: CaseBrief, error: str) -> str:
    return (
        f"Запуск по расписанию не выполнился: {error}\n"
        f"Кейс: {_title(due, brief)}{_late_suffix(due)}. "
        f"Инструкция: {due.instruction}"
    )


def _title(due: ScheduleDue, brief: CaseBrief) -> str:
    return brief.title or f"кейс {due.case_id}"


def _late_suffix(due: ScheduleDue) -> str:
    return f" (с опозданием на {due.late_minutes} мин)" if due.late else ""


def _late_note(due: ScheduleDue) -> str:
    return f", с опозданием на {due.late_minutes} мин" if due.late else ""


def _kind(due: ScheduleDue) -> str:
    if due.kind == "periodic":
        return f"периодическое, cron {due.cron} в поясе {due.timezone}"
    return "разовое"


def _moment(moment: datetime, zone: ZoneInfo) -> str:
    return moment.astimezone(zone).strftime(MOMENT_FORMAT)

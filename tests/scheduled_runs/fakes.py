import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pika
from pika.spec import Basic

from src.scheduled_runs.models import ScheduledRun
from src.scheduled_runs.services.due_parser import ScheduleDueParser
from src.scheduled_runs.services.executor import CaseBrief, ScheduledRunExecutor
from src.scheduled_runs.services.rabbitmq_consumer import RabbitMqScheduleDueConsumer
from tests.agent_notifications.recording_message_sender import RecordingMessageSender
from workers.scheduled_run.ai_run_model import AiRunModel
from workers.scheduled_run.owner_notifier import SplittingOwnerNotifier

OWNER_CHAT_ID = 42
RUN_ID = "0199d000-0000-7000-8000-000000000001"
SCHEDULER = "scheduler"


def due_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "v": 1,
        "run_id": RUN_ID,
        "schedule_id": "0199c000-0000-7000-8000-000000000002",
        "user": "sumarokov",
        "case_id": "0199a1b2-0000-7000-8000-000000000003",
        "task_event_id": None,
        "instruction": "Проверь почту: ответил ли нотариус по ТОО",
        "kind": "once",
        "cron": None,
        "timezone": "Asia/Almaty",
        "scheduled_for": "2026-10-02T05:00:00Z",
        "fired_at": "2026-10-02T05:00:21Z",
        "late": False,
    }
    body.update(changes)
    return body


def due_properties(**changes: Any) -> pika.BasicProperties:
    values: dict[str, Any] = {
        "message_id": RUN_ID,
        "user_id": SCHEDULER,
        "type": "schedule.due",
    }
    values.update(changes)
    return pika.BasicProperties(**values)


class InMemoryRunJournal:
    def __init__(self) -> None:
        self.runs: dict[str, ScheduledRun] = {}

    def start(self, run_id: str, schedule_id: str, case_id: str) -> ScheduledRun:
        if run_id not in self.runs:
            self.runs[run_id] = ScheduledRun(
                id=len(self.runs) + 1,
                run_id=run_id,
                schedule_id=schedule_id,
                case_id=case_id,
                started_at=datetime.now(tz=UTC),
                finished_at=None,
                delivered_at=None,
                error=None,
            )
        return self.runs[run_id]

    def finish(self, run_id: str, error: str | None) -> None:
        self.runs[run_id] = self.runs[run_id].model_copy(
            update={"finished_at": datetime.now(tz=UTC), "error": error}
        )

    def mark_delivered(self, run_id: str) -> None:
        self.runs[run_id] = self.runs[run_id].model_copy(
            update={"delivered_at": datetime.now(tz=UTC)}
        )


@dataclass
class StubAnswer:
    content: str | None


@dataclass
class FakeConversation:
    answer: str = "Нотариус ответил 01.10: документы готовы."
    failure: Exception | None = None
    calls: list[tuple[str, str, dict[str, Any] | None]] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)

    def update_system_prompt(self, text: str) -> None:
        self.prompts.append(text)

    def process_message(
        self,
        thread_id: str,
        user_message: str,
        tool_context: dict[str, Any] | None = None,
    ) -> StubAnswer:
        self.calls.append((thread_id, user_message, tool_context))
        if self.failure is not None:
            raise self.failure
        return StubAnswer(content=self.answer)


class FixedPrompt:
    def build(self) -> str:
        return "промпт запуска"


class StubBriefing:
    def brief(self, case_id: str) -> CaseBrief:
        return CaseBrief(title="ТОО", text=f"<лента кейса {case_id}>")


class RecordingChannel:
    def __init__(self) -> None:
        self.acked: list[int] = []
        self.rejected: list[tuple[int, bool]] = []

    def basic_ack(self, delivery_tag: int) -> None:
        self.acked.append(delivery_tag)

    def basic_reject(self, delivery_tag: int, requeue: bool) -> None:
        self.rejected.append((delivery_tag, requeue))


@dataclass
class ExecutorWorld:
    conversation: FakeConversation = field(default_factory=FakeConversation)
    journal: InMemoryRunJournal = field(default_factory=InMemoryRunJournal)
    sender: RecordingMessageSender = field(default_factory=RecordingMessageSender)
    channel: RecordingChannel = field(default_factory=RecordingChannel)

    def consumer(self) -> RabbitMqScheduleDueConsumer:
        return RabbitMqScheduleDueConsumer(
            amqp_url="amqp://unused",
            queue="schedule.sumarokov",
            handler=ScheduledRunExecutor(
                scheduler_account=SCHEDULER,
                parser=ScheduleDueParser(),
                journal=self.journal,
                briefing=StubBriefing(),
                model=AiRunModel(
                    conversation=self.conversation,
                    prompt=FixedPrompt(),
                    tool_context={"chat_id": OWNER_CHAT_ID, "user_id": OWNER_CHAT_ID},
                ),
                notifier=SplittingOwnerNotifier(
                    sender=self.sender,
                    splitter=_NoSplit(),
                    owner_chat_id=OWNER_CHAT_ID,
                ),
            ),
        )

    def deliver(
        self,
        body: dict[str, Any] | bytes | None = None,
        properties: pika.BasicProperties | None = None,
        delivery_tag: int = 7,
    ) -> None:
        raw = body if isinstance(body, bytes) else json.dumps(body or due_body())
        self.consumer().on_message(
            self.channel,
            Basic.Deliver(delivery_tag=delivery_tag),
            properties or due_properties(),
            raw.encode() if isinstance(raw, str) else raw,
        )

    @property
    def texts(self) -> list[str]:
        return [message.text for message in self.sender.sent]


class _NoSplit:
    def split(self, text: str) -> list[str]:
        return [text]

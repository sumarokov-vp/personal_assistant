from typing import Any

import pika
import pytest

from tests.scheduled_runs.fakes import (
    OWNER_CHAT_ID,
    RUN_ID,
    ExecutorWorld,
    due_body,
    due_properties,
)


def test_due_message_runs_model_once_and_tells_owner():
    world = ExecutorWorld()

    world.deliver()

    [(thread_id, request, tool_context)] = world.conversation.calls
    assert thread_id == f"schedule:{RUN_ID}"
    assert "Инструкция владельца: Проверь почту: ответил ли нотариус по ТОО" in request
    assert "назначено на 02.10.2026 10:00 (Asia/Almaty)" in request
    assert "<лента кейса 0199a1b2-0000-7000-8000-000000000003>" in request
    assert tool_context == {"chat_id": OWNER_CHAT_ID, "user_id": OWNER_CHAT_ID}
    assert world.conversation.prompts == ["промпт запуска"]
    assert world.texts == [
        "По расписанию · ТОО:\nНотариус ответил 01.10: документы готовы."
    ]
    assert world.sender.sent[0].chat_id == OWNER_CHAT_ID
    assert world.channel.acked == [7]
    run = world.journal.runs[RUN_ID]
    assert run.finished_at is not None
    assert run.delivered_at is not None
    assert run.error is None


def test_repeated_run_id_is_acked_without_second_run():
    world = ExecutorWorld()

    world.deliver(delivery_tag=7)
    world.deliver(delivery_tag=8)

    assert len(world.conversation.calls) == 1
    assert len(world.texts) == 1
    assert world.channel.acked == [7, 8]


def test_undelivered_run_is_run_again_after_redelivery():
    world = ExecutorWorld()
    world.journal.start(RUN_ID, "s", "c")

    world.deliver()

    assert len(world.conversation.calls) == 1
    assert world.channel.acked == [7]


@pytest.mark.parametrize(
    "properties",
    [
        due_properties(user_id="agent-mac-mini"),
        due_properties(user_id=None),
        due_properties(type="file"),
        due_properties(message_id=None),
        due_properties(message_id="another-run"),
    ],
    ids=["foreign-user", "no-user", "wrong-type", "no-message-id", "id-mismatch"],
)
def test_message_not_from_scheduler_is_rejected_without_requeue(
    properties: pika.BasicProperties,
):
    world = ExecutorWorld()

    world.deliver(properties=properties)

    assert world.conversation.calls == []
    assert world.texts == []
    assert world.journal.runs == {}
    assert world.channel.acked == []
    assert world.channel.rejected == [(7, False)]


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        due_body(v=2),
        due_body(instruction=""),
        due_body(kind="hourly"),
        due_body(timezone="Mars/Olympus"),
        due_body(scheduled_for="2026-10-02T05:00:00"),
        {key: value for key, value in due_body().items() if key != "case_id"},
    ],
    ids=["not-json", "v2", "empty-instruction", "kind", "timezone", "naive", "no-case"],
)
def test_body_off_schema_is_rejected_without_requeue(body: dict[str, Any] | bytes):
    world = ExecutorWorld()

    world.deliver(body=body)

    assert world.conversation.calls == []
    assert world.texts == []
    assert world.channel.rejected == [(7, False)]


def test_late_run_tells_owner_how_late():
    world = ExecutorWorld()

    world.deliver(
        body=due_body(
            scheduled_for="2026-10-02T05:00:00Z",
            fired_at="2026-10-02T07:03:10Z",
            late=True,
        )
    )

    [(_, request, _)] = world.conversation.calls
    assert "с опозданием на 123 мин" in request
    assert world.texts[0].startswith("По расписанию · ТОО (с опозданием на 123 мин):\n")


def test_periodic_run_names_its_cron():
    world = ExecutorWorld()

    world.deliver(body=due_body(kind="periodic", cron="0 10 * * 1#1"))

    [(_, request, _)] = world.conversation.calls
    assert "периодическое, cron 0 10 * * 1#1 в поясе Asia/Almaty" in request


def test_model_failure_tells_owner_error_type_and_acks():
    world = ExecutorWorld()
    world.conversation.failure = TimeoutError("CLI did not answer")

    world.deliver()

    assert world.texts == [
        "Запуск по расписанию не выполнился: TimeoutError\n"
        "Кейс: ТОО. Инструкция: Проверь почту: ответил ли нотариус по ТОО"
    ]
    assert world.channel.acked == [7]
    run = world.journal.runs[RUN_ID]
    assert run.error == "TimeoutError"
    assert run.delivered_at is not None


def test_empty_answer_still_reaches_owner():
    world = ExecutorWorld()
    world.conversation.answer = "  "

    world.deliver()

    assert world.texts == ["По расписанию · ТОО:\n(модель не дала ответа)"]

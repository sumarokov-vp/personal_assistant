from datetime import UTC, datetime

import pytest
from bot_framework import ParseMode

from src.agent_notifications.services.delivery import AgentNotificationDelivery
from src.agent_notifications.services.entities import (
    DeliveryOutcome,
    IncomingNotification,
)
from src.agent_notifications.services.text_splitter import TelegramTextSplitter
from tests.agent_notifications.in_memory_notification_journal import (
    InMemoryNotificationJournal,
)
from tests.agent_notifications.recording_message_sender import RecordingMessageSender

OWNER_CHAT_ID = 42


@pytest.fixture
def journal() -> InMemoryNotificationJournal:
    return InMemoryNotificationJournal()


@pytest.fixture
def sender() -> RecordingMessageSender:
    return RecordingMessageSender()


@pytest.fixture
def delivery(
    journal: InMemoryNotificationJournal, sender: RecordingMessageSender
) -> AgentNotificationDelivery:
    return AgentNotificationDelivery(
        journal=journal,
        message_sender=sender,
        splitter=TelegramTextSplitter(),
        owner_chat_id=OWNER_CHAT_ID,
    )


def notification(
    message_id: str | None = "m-1",
    sender: str | None = "agent-mac-mini",
    body: str = "Прогон кончился: 3 из 3 <b>зелёные</b>",
) -> IncomingNotification:
    return IncomingNotification(
        message_id=message_id,
        sender=sender,
        body=body,
        published_at=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
    )


def test_delivers_body_verbatim_under_source_line(
    delivery: AgentNotificationDelivery,
    journal: InMemoryNotificationJournal,
    sender: RecordingMessageSender,
) -> None:
    outcome = delivery.deliver(notification())

    assert outcome is DeliveryOutcome.DELIVERED
    assert [(m.chat_id, m.text, m.parse_mode) for m in sender.sent] == [
        (
            OWNER_CHAT_ID,
            "Агент mac-mini:\nПрогон кончился: 3 из 3 <b>зелёные</b>",
            ParseMode.PLAIN,
        )
    ]
    stored = journal.notifications["m-1"]
    assert stored.source == "mac-mini"
    assert stored.delivered_at is not None


def test_repeated_delivered_message_is_acknowledged_without_second_send(
    delivery: AgentNotificationDelivery, sender: RecordingMessageSender
) -> None:
    delivery.deliver(notification())

    outcome = delivery.deliver(notification())

    assert outcome is DeliveryOutcome.ALREADY_DELIVERED
    assert len(sender.sent) == 1


def test_recorded_but_undelivered_message_is_sent_on_redelivery(
    delivery: AgentNotificationDelivery,
    journal: InMemoryNotificationJournal,
    sender: RecordingMessageSender,
) -> None:
    journal.record(message_id="m-1", source="mac-mini", body="x", published_at=None)

    outcome = delivery.deliver(notification())

    assert outcome is DeliveryOutcome.DELIVERED
    assert len(sender.sent) == 1


@pytest.mark.parametrize(
    ("message_id", "source"), [("m-1", None), ("m-1", ""), (None, "agent-mac-mini")]
)
def test_rejects_without_user_id_or_message_id(
    delivery: AgentNotificationDelivery,
    journal: InMemoryNotificationJournal,
    sender: RecordingMessageSender,
    message_id: str | None,
    source: str | None,
) -> None:
    outcome = delivery.deliver(notification(message_id=message_id, sender=source))

    assert outcome is DeliveryOutcome.REJECTED
    assert sender.sent == []
    assert journal.notifications == {}


def test_long_text_goes_in_several_messages(
    delivery: AgentNotificationDelivery, sender: RecordingMessageSender
) -> None:
    body = "\n".join(f"строка {number:05d} " + "x" * 80 for number in range(200))

    delivery.deliver(notification(body=body))

    assert len(sender.sent) > 1
    assert all(len(message.text) <= 4096 for message in sender.sent)
    assert "".join(message.text for message in sender.sent) == (
        f"Агент mac-mini:\n{body}"
    )

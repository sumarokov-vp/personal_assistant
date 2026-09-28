from datetime import UTC, datetime

import pika
import pika.exceptions
import pytest

from src.colleague_mail.models import ColleagueMessageType
from src.colleague_mail.services.entities import MailSendOutcome
from src.colleague_mail.services.publisher import rabbitmq_mail_publisher
from src.colleague_mail.services.publisher.rabbitmq_mail_publisher import (
    RabbitMqMailPublisher,
)


class FakeChannel:
    def __init__(self, publish_error: Exception | None) -> None:
        self.publish_error = publish_error
        self.confirmed = False
        self.published: list[dict[str, object]] = []

    def confirm_delivery(self) -> None:
        self.confirmed = True

    def basic_publish(self, **kwargs: object) -> None:
        self.published.append(kwargs)
        if self.publish_error is not None:
            raise self.publish_error


class FakeConnection:
    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel
        self.is_open = True

    def channel(self) -> FakeChannel:
        return self._channel

    def close(self) -> None:
        self.is_open = False


def publish(monkeypatch: pytest.MonkeyPatch, connect: object) -> MailSendOutcome:
    monkeypatch.setattr(rabbitmq_mail_publisher.pika, "BlockingConnection", connect)
    return RabbitMqMailPublisher(
        mail_url="amqp://assistant-sumarokov:secret@localhost:5672/assistants.sumarokov",
        account="assistant-sumarokov",
    ).publish(
        message_id="m-1",
        recipient="yura",
        message_type=ColleagueMessageType.QUESTION,
        body=b"{}",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
    )


def test_confirmed_mandatory_publish_lands_in_inbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = FakeChannel(publish_error=None)
    connection = FakeConnection(channel)

    outcome = publish(monkeypatch, lambda parameters: connection)

    assert outcome is MailSendOutcome.IN_RECIPIENT_INBOX
    assert channel.confirmed
    [call] = channel.published
    assert call["exchange"] == "assistant-mail"
    assert call["routing_key"] == "yura"
    assert call["mandatory"] is True
    properties = call["properties"]
    assert isinstance(properties, pika.BasicProperties)
    assert (properties.user_id, properties.message_id, properties.type) == (
        "assistant-sumarokov",
        "m-1",
        "question",
    )
    assert not connection.is_open


def test_basic_return_means_no_recipient(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection(
        FakeChannel(publish_error=pika.exceptions.UnroutableError([]))
    )

    outcome = publish(monkeypatch, lambda parameters: connection)

    assert outcome is MailSendOutcome.NO_RECIPIENT
    assert not connection.is_open


def test_nack_means_broker_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection(
        FakeChannel(publish_error=pika.exceptions.NackError([]))
    )

    assert publish(monkeypatch, lambda parameters: connection) is (
        MailSendOutcome.BROKER_UNAVAILABLE
    )


def test_unreachable_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(parameters: object) -> FakeConnection:
        raise pika.exceptions.AMQPConnectionError("refused")

    assert publish(monkeypatch, refuse) is MailSendOutcome.BROKER_UNAVAILABLE

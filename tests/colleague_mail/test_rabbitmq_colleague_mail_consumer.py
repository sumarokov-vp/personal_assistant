from datetime import UTC, datetime

import pika
import pytest
from pika.spec import Basic

from src.colleague_mail.services.entities import IncomingMail, ReceiveOutcome
from src.colleague_mail.services.rabbitmq_consumer import (
    RabbitMqColleagueMailConsumer,
)


class StubReceiver:
    def __init__(self, outcome: ReceiveOutcome) -> None:
        self.outcome = outcome
        self.received: list[IncomingMail] = []

    def receive(self, incoming: IncomingMail) -> ReceiveOutcome:
        self.received.append(incoming)
        return self.outcome


class RecordingChannel:
    def __init__(self) -> None:
        self.acked: list[int] = []
        self.rejected: list[tuple[int, bool]] = []

    def basic_ack(self, delivery_tag: int) -> None:
        self.acked.append(delivery_tag)

    def basic_reject(self, delivery_tag: int, requeue: bool) -> None:
        self.rejected.append((delivery_tag, requeue))


def consume_one(
    outcome: ReceiveOutcome, properties: pika.BasicProperties
) -> tuple[StubReceiver, RecordingChannel]:
    receiver = StubReceiver(outcome)
    channel = RecordingChannel()
    RabbitMqColleagueMailConsumer(
        mail_url="amqp://unused", inbox="inbox.sumarokov", receiver=receiver
    ).on_message(channel, Basic.Deliver(delivery_tag=7), properties, b"{}")
    return receiver, channel


@pytest.mark.parametrize("outcome", [ReceiveOutcome.RECORDED, ReceiveOutcome.DUPLICATE])
def test_passes_broker_properties_and_acks(outcome: ReceiveOutcome) -> None:
    receiver, channel = consume_one(
        outcome,
        pika.BasicProperties(
            user_id="assistant-yura", message_id="m-1", timestamp=1790000000
        ),
    )

    assert receiver.received == [
        IncomingMail(
            message_id="m-1",
            user_id="assistant-yura",
            body=b"{}",
            published_at=datetime.fromtimestamp(1790000000, tz=UTC),
        )
    ]
    assert channel.acked == [7]
    assert channel.rejected == []


def test_rejects_without_requeue() -> None:
    _, channel = consume_one(
        ReceiveOutcome.REJECTED, pika.BasicProperties(message_id="m-1")
    )

    assert channel.acked == []
    assert channel.rejected == [(7, False)]

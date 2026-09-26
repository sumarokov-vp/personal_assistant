from datetime import UTC, datetime

import pika
from pika.spec import Basic

from src.agent_notifications.services.entities import (
    DeliveryOutcome,
    IncomingNotification,
)
from src.agent_notifications.services.rabbitmq_consumer import (
    RabbitMqNotificationConsumer,
)


class StubDelivery:
    def __init__(self, outcome: DeliveryOutcome) -> None:
        self.outcome = outcome
        self.received: list[IncomingNotification] = []

    def deliver(self, incoming: IncomingNotification) -> DeliveryOutcome:
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
    outcome: DeliveryOutcome, properties: pika.BasicProperties
) -> tuple[StubDelivery, RecordingChannel]:
    delivery = StubDelivery(outcome)
    channel = RecordingChannel()
    RabbitMqNotificationConsumer(
        rabbitmq_url="amqp://unused", delivery=delivery
    ).on_message(channel, Basic.Deliver(delivery_tag=7), properties, "текст".encode())
    return delivery, channel


def test_passes_broker_properties_and_acks_delivered() -> None:
    delivery, channel = consume_one(
        DeliveryOutcome.DELIVERED,
        pika.BasicProperties(
            user_id="agent-mac-mini", message_id="m-1", timestamp=1790000000
        ),
    )

    assert delivery.received == [
        IncomingNotification(
            message_id="m-1",
            sender="agent-mac-mini",
            body="текст",
            published_at=datetime.fromtimestamp(1790000000, tz=UTC),
        )
    ]
    assert channel.acked == [7]
    assert channel.rejected == []


def test_rejects_without_requeue_when_delivery_refuses() -> None:
    _, channel = consume_one(
        DeliveryOutcome.REJECTED, pika.BasicProperties(message_id="m-1")
    )

    assert channel.acked == []
    assert channel.rejected == [(7, False)]

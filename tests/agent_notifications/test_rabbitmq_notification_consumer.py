from datetime import UTC, datetime

import pika
from pika.spec import Basic

from src.agent_notifications.services.entities import (
    DeliveryOutcome,
    IncomingAttachment,
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
    outcome: DeliveryOutcome,
    properties: pika.BasicProperties,
    body: bytes = "текст".encode(),
) -> tuple[StubDelivery, RecordingChannel]:
    delivery = StubDelivery(outcome)
    channel = RecordingChannel()
    RabbitMqNotificationConsumer(
        rabbitmq_url="amqp://unused", delivery=delivery
    ).on_message(channel, Basic.Deliver(delivery_tag=7), properties, body)
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


def test_file_message_keeps_raw_bytes_and_headers() -> None:
    pdf = b"%PDF-1.7\xff\xfe\x00"
    delivery, channel = consume_one(
        DeliveryOutcome.DELIVERED,
        pika.BasicProperties(
            user_id="agent-mac-mini",
            message_id="f-1",
            type="file",
            headers={"filename": "отчёт.pdf".encode(), "caption": "за сентябрь"},
        ),
        body=pdf,
    )

    assert delivery.received == [
        IncomingNotification(
            message_id="f-1",
            sender="agent-mac-mini",
            body="за сентябрь",
            published_at=None,
            attachment=IncomingAttachment(
                filename="отчёт.pdf", content=pdf, path=None, declared_size=None
            ),
        )
    ]
    assert channel.acked == [7]


def test_file_message_by_path_carries_path_and_declared_size() -> None:
    delivery, _ = consume_one(
        DeliveryOutcome.DELIVERED,
        pika.BasicProperties(
            user_id="agent-mac-mini",
            message_id="f-2",
            type="file",
            headers={
                "filename": "big.zip",
                "path": "Personal Assistant/agents/big.zip",
                "size": 20971520,
            },
        ),
        body=b"",
    )

    attachment = delivery.received[0].attachment
    assert attachment == IncomingAttachment(
        filename="big.zip",
        content=b"",
        path="Personal Assistant/agents/big.zip",
        declared_size=20971520,
    )
    assert delivery.received[0].body == ""

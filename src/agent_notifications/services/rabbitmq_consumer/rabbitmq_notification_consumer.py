from collections.abc import Mapping
from datetime import UTC, datetime
from logging import getLogger

import pika
from pika.spec import Basic, BasicProperties

from src.agent_notifications.services.entities.delivery_outcome import DeliveryOutcome
from src.agent_notifications.services.entities.incoming_attachment import (
    IncomingAttachment,
)
from src.agent_notifications.services.entities.incoming_notification import (
    IncomingNotification,
)
from src.agent_notifications.services.rabbitmq_consumer.protocols.i_delivery_channel import (
    IDeliveryChannel,
)
from src.agent_notifications.services.rabbitmq_consumer.protocols.i_notification_delivery import (
    INotificationDelivery,
)

logger = getLogger(__name__)

NOTIFICATIONS_QUEUE = "pa.notifications"
FILE_MESSAGE_TYPE = "file"


class RabbitMqNotificationConsumer:
    def __init__(
        self,
        rabbitmq_url: str,
        delivery: INotificationDelivery,
        queue: str = NOTIFICATIONS_QUEUE,
    ) -> None:
        self._rabbitmq_url = rabbitmq_url
        self._delivery = delivery
        self._queue = queue

    def consume(self) -> None:
        with pika.BlockingConnection(
            pika.URLParameters(self._rabbitmq_url)
        ) as connection:
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=self._queue, on_message_callback=self.on_message, auto_ack=False
            )
            logger.info("Consuming agent notifications from %s", self._queue)
            channel.start_consuming()

    def on_message(
        self,
        channel: IDeliveryChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
    ) -> None:
        outcome = self._delivery.deliver(_incoming(properties, body))
        if outcome is DeliveryOutcome.REJECTED:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)


def _incoming(properties: BasicProperties, body: bytes) -> IncomingNotification:
    if properties.type != FILE_MESSAGE_TYPE:
        return IncomingNotification(
            message_id=properties.message_id,
            sender=properties.user_id,
            body=body.decode("utf-8", errors="replace"),
            published_at=_published_at(properties.timestamp),
        )
    headers: Mapping[str, object] = properties.headers or {}
    return IncomingNotification(
        message_id=properties.message_id,
        sender=properties.user_id,
        body=_text_header(headers, "caption") or "",
        published_at=_published_at(properties.timestamp),
        attachment=IncomingAttachment(
            filename=_text_header(headers, "filename"),
            content=body,
            path=_text_header(headers, "path"),
            declared_size=_int_header(headers, "size"),
        ),
    )


def _text_header(headers: Mapping[str, object], name: str) -> str | None:
    value = headers.get(name)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return None


def _int_header(headers: Mapping[str, object], name: str) -> int | None:
    value = headers.get(name)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text_header(headers, name)
    if text is not None and text.strip().isdigit():
        return int(text)
    return None


def _published_at(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC)

from datetime import UTC, datetime
from logging import getLogger

import pika
from pika.spec import Basic, BasicProperties

from src.agent_notifications.services.entities.delivery_outcome import DeliveryOutcome
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
        outcome = self._delivery.deliver(
            IncomingNotification(
                message_id=properties.message_id,
                sender=properties.user_id,
                body=body.decode("utf-8", errors="replace"),
                published_at=_published_at(properties.timestamp),
            )
        )
        if outcome is DeliveryOutcome.REJECTED:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)


def _published_at(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC)

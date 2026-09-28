from datetime import UTC, datetime
from logging import getLogger

import pika
from pika.spec import Basic, BasicProperties

from src.colleague_mail.services.entities.incoming_mail import IncomingMail
from src.colleague_mail.services.entities.receive_outcome import ReceiveOutcome
from src.colleague_mail.services.rabbitmq_consumer.protocols.i_delivery_channel import (
    IDeliveryChannel,
)
from src.colleague_mail.services.rabbitmq_consumer.protocols.i_incoming_mail_receiver import (
    IIncomingMailReceiver,
)

logger = getLogger(__name__)


class RabbitMqColleagueMailConsumer:
    def __init__(
        self, mail_url: str, inbox: str, receiver: IIncomingMailReceiver
    ) -> None:
        self._mail_url = mail_url
        self._inbox = inbox
        self._receiver = receiver

    def consume(self) -> None:
        with pika.BlockingConnection(pika.URLParameters(self._mail_url)) as connection:
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=self._inbox, on_message_callback=self.on_message, auto_ack=False
            )
            logger.info("Consuming colleague mail from %s", self._inbox)
            channel.start_consuming()

    def on_message(
        self,
        channel: IDeliveryChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
    ) -> None:
        outcome = self._receiver.receive(
            IncomingMail(
                message_id=properties.message_id,
                user_id=properties.user_id,
                body=body,
                published_at=_published_at(properties.timestamp),
            )
        )
        if outcome is ReceiveOutcome.REJECTED:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)


def _published_at(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC)

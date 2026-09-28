from datetime import datetime
from logging import getLogger

import pika
import pika.exceptions

from src.colleague_mail.models.colleague_message_type import ColleagueMessageType
from src.colleague_mail.services.entities.mail_send_outcome import MailSendOutcome

logger = getLogger(__name__)

MAIL_EXCHANGE = "assistant-mail"
CONNECT_TIMEOUT_SECONDS = 10
BLOCKED_CONNECTION_TIMEOUT_SECONDS = 15


class RabbitMqMailPublisher:
    def __init__(
        self, mail_url: str, account: str, exchange: str = MAIL_EXCHANGE
    ) -> None:
        self._mail_url = mail_url
        self._account = account
        self._exchange = exchange

    def publish(
        self,
        message_id: str,
        recipient: str,
        message_type: ColleagueMessageType,
        body: bytes,
        published_at: datetime,
    ) -> MailSendOutcome:
        try:
            connection = pika.BlockingConnection(self._parameters())
        except pika.exceptions.AMQPError:
            logger.exception("Colleague mail broker unreachable")
            return MailSendOutcome.BROKER_UNAVAILABLE
        try:
            channel = connection.channel()
            channel.confirm_delivery()
            channel.basic_publish(
                exchange=self._exchange,
                routing_key=recipient,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    content_encoding="utf-8",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    message_id=message_id,
                    user_id=self._account,
                    timestamp=int(published_at.timestamp()),
                    type=message_type.value,
                ),
                mandatory=True,
            )
        except pika.exceptions.UnroutableError:
            logger.warning(
                "Colleague mail %s returned: no inbox for %r", message_id, recipient
            )
            return MailSendOutcome.NO_RECIPIENT
        except pika.exceptions.AMQPError:
            logger.exception("Colleague mail %s not confirmed by broker", message_id)
            return MailSendOutcome.BROKER_UNAVAILABLE
        finally:
            if connection.is_open:
                connection.close()
        return MailSendOutcome.IN_RECIPIENT_INBOX

    def _parameters(self) -> pika.URLParameters:
        parameters = pika.URLParameters(self._mail_url)
        parameters.connection_attempts = 1
        parameters.socket_timeout = CONNECT_TIMEOUT_SECONDS
        parameters.blocked_connection_timeout = BLOCKED_CONNECTION_TIMEOUT_SECONDS
        return parameters

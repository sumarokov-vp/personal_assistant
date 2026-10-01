from logging import getLogger

import pika
from pika.spec import Basic, BasicProperties

from src.scheduled_runs.services.entities.due_outcome import DueOutcome
from src.scheduled_runs.services.entities.incoming_due import IncomingDue
from src.scheduled_runs.services.rabbitmq_consumer.protocols.i_delivery_channel import (
    IDeliveryChannel,
)
from src.scheduled_runs.services.rabbitmq_consumer.protocols.i_due_handler import (
    IDueHandler,
)

logger = getLogger(__name__)

# Прогон модели длится минуты, а BlockingConnection внутри обработчика сердцебиения не шлёт:
# брокер закрыл бы соединение посреди прогона. Сердцебиение выключено, повтор после обрыва
# отсекает журнал по run_id
NO_HEARTBEAT = 0


class RabbitMqScheduleDueConsumer:
    def __init__(self, amqp_url: str, queue: str, handler: IDueHandler) -> None:
        self._amqp_url = amqp_url
        self._queue = queue
        self._handler = handler

    def consume(self) -> None:
        parameters = pika.URLParameters(self._amqp_url)
        parameters.heartbeat = NO_HEARTBEAT
        with pika.BlockingConnection(parameters) as connection:
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=self._queue, on_message_callback=self.on_message, auto_ack=False
            )
            logger.info("Consuming schedule due messages from %s", self._queue)
            channel.start_consuming()

    def on_message(
        self,
        channel: IDeliveryChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
    ) -> None:
        outcome = self._handler.handle(
            IncomingDue(
                message_id=properties.message_id,
                sender=properties.user_id,
                message_type=properties.type,
                body=body,
            )
        )
        if outcome is DueOutcome.REJECTED:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)

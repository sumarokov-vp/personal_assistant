import time
import uuid
from urllib.parse import unquote, urlsplit

import aio_pika
from aio_pika import DeliveryMode, Message

NOTIFY_EXCHANGE = "agent-notify"
CONNECT_SECONDS = 10.0
CONFIRM_SECONDS = 15.0


class AmqpNoticePublisher:
    def __init__(self, amqp_url: str, exchange: str = NOTIFY_EXCHANGE) -> None:
        self._amqp_url = amqp_url
        self._exchange = exchange
        self._user = unquote(urlsplit(amqp_url).username or "")

    async def publish(self, text: str) -> None:
        connection = await aio_pika.connect(self._amqp_url, timeout=CONNECT_SECONDS)
        async with connection:
            channel = await connection.channel(
                publisher_confirms=True, on_return_raises=True
            )
            exchange = await channel.get_exchange(self._exchange, ensure=False)
            await exchange.publish(
                Message(
                    body=text.encode("utf-8"),
                    content_type="text/plain",
                    content_encoding="utf-8",
                    delivery_mode=DeliveryMode.PERSISTENT,
                    user_id=self._user,
                    message_id=str(uuid.uuid4()),
                    timestamp=int(time.time()),
                ),
                routing_key="",
                mandatory=True,
                timeout=CONFIRM_SECONDS,
            )

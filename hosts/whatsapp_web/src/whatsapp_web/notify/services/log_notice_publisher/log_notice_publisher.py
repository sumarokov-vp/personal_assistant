import logging

logger = logging.getLogger(__name__)


class LogNoticePublisher:
    async def publish(self, text: str) -> None:
        logger.warning("owner notice (no notify_amqp_url, not sent): %s", text)

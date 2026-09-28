import asyncio
import logging

from whatsapp_web.notify.services.background_owner_notifier.protocols.i_notice_publisher import (
    INoticePublisher,
)

logger = logging.getLogger(__name__)


class BackgroundOwnerNotifier:
    def __init__(self, publisher: INoticePublisher) -> None:
        self._publisher = publisher
        self._pending: set[asyncio.Task[None]] = set()
        self._in_order = asyncio.Lock()

    def notify(self, text: str) -> None:
        sending = asyncio.create_task(self._publish_in_order(text))
        self._pending.add(sending)
        sending.add_done_callback(lambda done: self._sent(done, text))

    async def drain(self) -> None:
        if self._pending:
            await asyncio.wait(set(self._pending))

    async def _publish_in_order(self, text: str) -> None:
        async with self._in_order:
            await self._publisher.publish(text)

    def _sent(self, sending: asyncio.Task[None], text: str) -> None:
        self._pending.discard(sending)
        if sending.cancelled():
            return
        error = sending.exception()
        if error is not None:
            logger.error("owner notice not published (%r): %s", error, text)

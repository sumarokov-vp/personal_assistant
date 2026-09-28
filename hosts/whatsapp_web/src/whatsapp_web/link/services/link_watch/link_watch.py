import logging

from whatsapp_web.link.services.link_watch.protocols.i_link_refresh import (
    ILinkRefresh,
)
from whatsapp_web.link.services.link_watch.protocols.i_relink_attempts import (
    IRelinkAttempts,
)

logger = logging.getLogger(__name__)


class LinkWatch:
    def __init__(self, link_status: ILinkRefresh, relink: IRelinkAttempts) -> None:
        self._link_status = link_status
        self._relink = relink

    async def check(self) -> None:
        if self._relink.attempt_running():
            return
        state = await self._link_status.refresh()
        logger.info("scheduled link check: linked=%s", state.linked)
        if not state.linked:
            self._relink.request_attempt(force=False)

from typing import Protocol

from whatsapp_web.browser.models.link_state import LinkState


class ILinkStateListener(Protocol):
    async def link_changed(self, state: LinkState) -> None: ...

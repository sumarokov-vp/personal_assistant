from typing import Protocol

from whatsapp_web.browser.models.link_state import LinkState


class ILinkScreen(Protocol):
    async def link_state(self) -> LinkState: ...

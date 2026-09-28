from typing import Protocol

from whatsapp_web.browser.models.link_state import LinkState


class ILinkStatus(Protocol):
    async def current(self) -> LinkState: ...

from typing import Protocol

from whatsapp_web.browser.models.link_state import LinkState


class ILinkRefresh(Protocol):
    async def refresh(self) -> LinkState: ...

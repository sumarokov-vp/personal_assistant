from typing import Protocol

from whatsapp_web.browser.models.link_state import LinkState


class ILinkStateRecorder(Protocol):
    async def record(self, state: LinkState) -> None: ...

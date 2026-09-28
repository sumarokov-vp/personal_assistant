from typing import Protocol

from whatsapp_web.browser.models.link_state import LinkState


class IRelinkScreen(Protocol):
    async def link_state(self) -> LinkState: ...

    async def request_phone_code(self, phone: str) -> str: ...

    async def current_link_code(self) -> str | None: ...

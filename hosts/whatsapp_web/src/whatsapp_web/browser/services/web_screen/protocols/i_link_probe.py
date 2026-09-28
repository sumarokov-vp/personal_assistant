from typing import Protocol

from playwright.async_api import Page

from whatsapp_web.browser.models.link_state import LinkState


class ILinkProbe(Protocol):
    async def probe(self, page: Page) -> LinkState: ...

from typing import Protocol

from whatsapp_web.browser.models.link_state import LinkState


class ILastLinkState(Protocol):
    def last(self) -> LinkState | None: ...

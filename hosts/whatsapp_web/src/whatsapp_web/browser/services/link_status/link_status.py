from whatsapp_web.browser.models.link_state import LinkState
from whatsapp_web.browser.services.link_status.protocols.i_last_link_state import (
    ILastLinkState,
)
from whatsapp_web.browser.services.link_status.protocols.i_link_screen_lease import (
    ILinkScreenLease,
)


class LinkStatus:
    def __init__(self, last_state: ILastLinkState, screens: ILinkScreenLease) -> None:
        self._last_state = last_state
        self._screens = screens

    async def current(self) -> LinkState:
        known = self._last_state.last()
        if known is not None:
            return known
        return await self.refresh()

    async def refresh(self) -> LinkState:
        async with self._screens.lease() as screen:
            return await screen.link_state()

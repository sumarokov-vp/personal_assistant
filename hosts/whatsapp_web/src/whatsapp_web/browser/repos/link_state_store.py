from whatsapp_web.browser.models.link_state import LinkState
from whatsapp_web.browser.repos.protocols.i_link_state_listener import (
    ILinkStateListener,
)


class LinkStateStore:
    def __init__(self) -> None:
        self._last: LinkState | None = None
        self._listeners: list[ILinkStateListener] = []

    def add_listener(self, listener: ILinkStateListener) -> None:
        self._listeners.append(listener)

    def last(self) -> LinkState | None:
        return self._last

    async def record(self, state: LinkState) -> None:
        previous = self._last
        self._last = state
        if previous is not None and previous.linked == state.linked:
            return
        for listener in self._listeners:
            await listener.link_changed(state)

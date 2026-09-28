from contextlib import AbstractAsyncContextManager
from typing import Protocol

from whatsapp_web.browser.services.link_status.protocols.i_link_screen import (
    ILinkScreen,
)


class ILinkScreenLease(Protocol):
    def lease(self) -> AbstractAsyncContextManager[ILinkScreen]: ...

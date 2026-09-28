from contextlib import AbstractAsyncContextManager
from typing import Protocol

from whatsapp_web.link.services.relink_coordinator.protocols.i_relink_screen import (
    IRelinkScreen,
)


class IRelinkScreenLease(Protocol):
    def lease(self) -> AbstractAsyncContextManager[IRelinkScreen]: ...

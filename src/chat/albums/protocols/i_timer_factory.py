from collections.abc import Callable
from typing import Protocol

from src.chat.albums.protocols.i_cancellable_timer import ICancellableTimer


class ITimerFactory(Protocol):
    def start(
        self, delay_seconds: float, callback: Callable[[], None]
    ) -> ICancellableTimer: ...

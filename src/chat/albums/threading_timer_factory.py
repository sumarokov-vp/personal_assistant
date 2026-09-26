from collections.abc import Callable
from threading import Timer

from src.chat.albums.protocols.i_cancellable_timer import ICancellableTimer


class ThreadingTimerFactory:
    def start(
        self, delay_seconds: float, callback: Callable[[], None]
    ) -> ICancellableTimer:
        timer = Timer(delay_seconds, callback)
        timer.daemon = True
        timer.start()
        return timer

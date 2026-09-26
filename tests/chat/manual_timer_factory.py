from collections.abc import Callable


class ManualTimer:
    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self) -> None:
        self.callback()


class ManualTimerFactory:
    def __init__(self) -> None:
        self.timers: list[ManualTimer] = []

    def start(self, delay_seconds: float, callback: Callable[[], None]) -> ManualTimer:
        timer = ManualTimer(callback)
        self.timers.append(timer)
        return timer

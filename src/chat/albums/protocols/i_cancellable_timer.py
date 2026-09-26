from typing import Protocol


class ICancellableTimer(Protocol):
    def cancel(self) -> None: ...

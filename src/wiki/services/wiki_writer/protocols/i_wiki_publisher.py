from typing import Protocol


class IWikiPublisher(Protocol):
    def refresh(self) -> None: ...

    def publish(self) -> None: ...

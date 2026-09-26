from typing import Protocol


class IWikiRefresher(Protocol):
    def refresh(self) -> None: ...

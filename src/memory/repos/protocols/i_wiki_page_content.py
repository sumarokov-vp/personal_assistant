from typing import Protocol


class IWikiPageContent(Protocol):
    @property
    def content(self) -> str: ...

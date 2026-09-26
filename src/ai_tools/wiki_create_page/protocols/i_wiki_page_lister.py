from typing import Protocol

from src.wiki import WikiPage


class IWikiPageLister(Protocol):
    def read_all_pages(self) -> list[WikiPage]: ...

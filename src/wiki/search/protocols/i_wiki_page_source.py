from typing import Protocol

from src.wiki.models.wiki_page import WikiPage


class IWikiPageSource(Protocol):
    def read_all_pages(self) -> list[WikiPage]: ...

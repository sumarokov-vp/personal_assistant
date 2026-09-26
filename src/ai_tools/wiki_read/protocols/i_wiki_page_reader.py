from typing import Protocol

from src.wiki.models.wiki_page import WikiPage


class IWikiPageReader(Protocol):
    def read_page(self, relative_path: str) -> WikiPage: ...

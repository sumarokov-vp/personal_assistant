from typing import Protocol

from src.wiki import WikiWriteResult


class IWikiPageCreator(Protocol):
    def create_page(
        self, relative_path: str, content: str, summary: str
    ) -> WikiWriteResult: ...

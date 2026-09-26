from typing import Protocol

from src.wiki import WikiWriteResult


class IWikiPageAppender(Protocol):
    def append_to_page(
        self, relative_path: str, text: str, summary: str
    ) -> WikiWriteResult: ...

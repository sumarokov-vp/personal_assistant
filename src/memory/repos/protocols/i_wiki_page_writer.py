from typing import Protocol


class IWikiPageWriter(Protocol):
    def write_page(self, relative_path: str, content: str, summary: str) -> object: ...

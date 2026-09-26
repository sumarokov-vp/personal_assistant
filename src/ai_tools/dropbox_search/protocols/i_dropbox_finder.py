from typing import Protocol

from src.dropbox.services.search.search_result import SearchResult


class IDropboxFinder(Protocol):
    def find(self, query: str, limit: int = 30, within: str = "") -> SearchResult: ...

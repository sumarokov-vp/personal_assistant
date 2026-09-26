from typing import Protocol

from src.wiki.search.wiki_search_hit import WikiSearchHit


class IWikiSearcher(Protocol):
    def search(self, query: str, limit: int) -> list[WikiSearchHit]: ...

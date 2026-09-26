from pydantic import BaseModel

from src.dropbox.services.search.search_hit import SearchHit


class SearchResult(BaseModel):
    query: str
    hits: list[SearchHit]
    total: int

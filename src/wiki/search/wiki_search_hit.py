from dataclasses import dataclass


@dataclass(frozen=True)
class WikiSearchHit:
    path: str
    title: str
    snippet: str

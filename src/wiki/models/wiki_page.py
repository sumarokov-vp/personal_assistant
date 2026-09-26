from dataclasses import dataclass


@dataclass(frozen=True)
class WikiPage:
    path: str
    content: str

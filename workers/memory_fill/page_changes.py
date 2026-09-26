from dataclasses import dataclass


@dataclass(frozen=True)
class PageChanges:
    title: str
    added: int
    updated: int

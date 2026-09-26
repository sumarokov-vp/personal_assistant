from dataclasses import dataclass


@dataclass(frozen=True)
class PageSnapshot:
    entries: dict[tuple[str, ...], object]

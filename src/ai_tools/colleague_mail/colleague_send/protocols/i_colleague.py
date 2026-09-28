from typing import Protocol


class IColleague(Protocol):
    @property
    def key(self) -> str: ...

    @property
    def editor(self) -> bool: ...

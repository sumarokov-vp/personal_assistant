from typing import Protocol


class ITakenWorkFile(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def media_type(self) -> str: ...

    @property
    def size(self) -> int: ...

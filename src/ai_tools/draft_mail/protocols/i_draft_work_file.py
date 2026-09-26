from typing import Protocol


class IDraftWorkFile(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def media_type(self) -> str: ...

    @property
    def size(self) -> int: ...

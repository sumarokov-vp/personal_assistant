from typing import Protocol


class IFetchedFile(Protocol):
    @property
    def content(self) -> bytes: ...

    @property
    def name(self) -> str: ...

    @property
    def media_type(self) -> str: ...

    @property
    def origin(self) -> str: ...

from typing import Protocol


class IWorkFileInfo(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def media_type(self) -> str: ...

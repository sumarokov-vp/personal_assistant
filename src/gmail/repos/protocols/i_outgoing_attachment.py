from typing import Protocol


class IOutgoingAttachment(Protocol):
    @property
    def key(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def media_type(self) -> str: ...

    @property
    def content(self) -> bytes: ...

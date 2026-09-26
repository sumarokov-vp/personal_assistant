from typing import Protocol


class IMailAttachment(Protocol):
    @property
    def attachment_id(self) -> str: ...

    @property
    def filename(self) -> str: ...

    @property
    def media_type(self) -> str: ...

    @property
    def size(self) -> int: ...

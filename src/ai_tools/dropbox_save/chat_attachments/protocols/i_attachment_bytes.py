from typing import Protocol


class IAttachmentBytes(Protocol):
    def get(self, key: str) -> bytes: ...

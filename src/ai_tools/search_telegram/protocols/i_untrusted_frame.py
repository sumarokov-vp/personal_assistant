from typing import Protocol


class IUntrustedFrame(Protocol):
    def wrap(self, content: str) -> str: ...

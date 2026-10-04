from typing import Protocol


class IAllowlist(Protocol):
    def contains(self, email: str) -> bool: ...

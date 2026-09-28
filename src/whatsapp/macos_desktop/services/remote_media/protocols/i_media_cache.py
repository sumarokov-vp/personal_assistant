from pathlib import Path
from typing import Protocol


class IMediaCache(Protocol):
    def find(self, key: str) -> Path | None: ...

    def store(self, key: str, content: bytes) -> None: ...

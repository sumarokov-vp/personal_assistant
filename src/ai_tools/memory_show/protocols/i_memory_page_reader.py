from typing import Protocol

from src.memory.repos import MemoryPageRead


class IMemoryPageReader[T](Protocol):
    @property
    def path(self) -> str: ...

    def read(self) -> MemoryPageRead[T]: ...

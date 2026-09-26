from typing import Protocol

from src.memory.repos import MemoryPageRead


class IMemoryPage[T](Protocol):
    def read(self) -> MemoryPageRead[T]: ...

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryPageRead[T]:
    entries: list[T]
    remarks: list[str]

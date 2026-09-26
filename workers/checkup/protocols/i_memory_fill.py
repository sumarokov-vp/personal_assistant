from typing import Protocol

from workers.checkup.protocols.i_memory_fill_summary import IMemoryFillSummary


class IMemoryFill(Protocol):
    def execute(self) -> IMemoryFillSummary: ...

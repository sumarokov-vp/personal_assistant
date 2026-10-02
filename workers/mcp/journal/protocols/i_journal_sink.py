from typing import Protocol


class IJournalSink(Protocol):
    def append(self, line: str) -> None: ...

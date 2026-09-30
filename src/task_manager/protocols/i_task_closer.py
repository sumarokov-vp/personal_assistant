from typing import Protocol


class ITaskCloser(Protocol):
    def close_task(self, ref: str) -> None: ...

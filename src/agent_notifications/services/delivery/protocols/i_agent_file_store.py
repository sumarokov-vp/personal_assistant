from typing import Protocol


class IAgentFileStore(Protocol):
    def refusal(self, path: str) -> str | None: ...

    def read(self, path: str) -> bytes | None: ...

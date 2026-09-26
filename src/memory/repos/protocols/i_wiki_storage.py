from typing import Protocol


class IWikiStorage(Protocol):
    def read(self, path: str) -> str | None: ...

    def write(self, path: str, content: str, commit_message: str) -> None: ...

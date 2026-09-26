from pathlib import Path
from typing import Protocol


class IDropboxDirectoryBoundary(Protocol):
    def resolve(self, path: str) -> Path: ...

    def relative(self, path: Path) -> str: ...

    def visible_children(self, directory: Path) -> list[Path]: ...

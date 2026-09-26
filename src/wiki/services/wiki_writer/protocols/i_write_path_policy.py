from pathlib import Path
from typing import Protocol


class IWritePathPolicy(Protocol):
    def resolve_for_write(self, relative_path: str) -> Path: ...

    def relative_name(self, path: Path) -> str: ...

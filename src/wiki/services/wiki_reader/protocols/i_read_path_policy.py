from pathlib import Path
from typing import Protocol


class IReadPathPolicy(Protocol):
    def resolve_for_read(self, relative_path: str) -> Path: ...

    def relative_name(self, path: Path) -> str: ...

    def is_readable_page(self, path: Path) -> bool: ...

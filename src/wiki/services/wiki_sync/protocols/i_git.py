from pathlib import Path
from typing import Protocol


class IGit(Protocol):
    def run_checked(self, *args: str, cwd: Path | None = None) -> str: ...

    def succeeds(self, *args: str, cwd: Path | None = None) -> bool: ...

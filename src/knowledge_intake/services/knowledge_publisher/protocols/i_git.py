from pathlib import Path
from typing import Protocol


class IGit(Protocol):
    @property
    def last_error(self) -> str: ...

    def run_checked(self, *args: str, cwd: Path | None = None) -> str: ...

    def succeeds(self, *args: str, cwd: Path | None = None) -> bool: ...

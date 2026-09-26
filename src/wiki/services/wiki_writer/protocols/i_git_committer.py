from pathlib import Path
from typing import Protocol


class IGitCommitter(Protocol):
    def run_checked(self, *args: str, cwd: Path | None = None) -> str: ...

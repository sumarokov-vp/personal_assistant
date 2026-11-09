from pathlib import Path
from typing import Protocol


class ITranscriptArchive(Protocol):
    def resolve(self, path: str) -> Path: ...

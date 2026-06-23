from pathlib import Path
from typing import Protocol


class ITranscriber(Protocol):
    def __call__(self, audio_path: Path) -> str: ...

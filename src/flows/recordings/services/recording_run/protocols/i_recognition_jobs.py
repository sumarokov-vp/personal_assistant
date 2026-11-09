from pathlib import Path
from typing import Any, Protocol


class IRecognitionJobs(Protocol):
    def submit(self, audio_path: Path, language: str | None = None) -> str: ...

    def wait_for_result(
        self, job_id: str, poll_interval: float = ..., max_wait: float = ...
    ) -> dict[str, Any]: ...

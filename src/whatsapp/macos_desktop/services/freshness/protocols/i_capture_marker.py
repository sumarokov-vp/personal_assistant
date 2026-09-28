from datetime import datetime
from typing import Protocol


class ICaptureMarker(Protocol):
    def captured_at(self) -> datetime | None: ...

from datetime import datetime
from pathlib import Path


class SnapshotMarker:
    def __init__(self, marker_path: Path) -> None:
        self._marker_path = marker_path

    def captured_at(self) -> datetime | None:
        if not self._marker_path.is_file():
            return None
        stamp = self._marker_path.read_text(encoding="utf-8").strip()
        return datetime.fromisoformat(stamp) if stamp else None

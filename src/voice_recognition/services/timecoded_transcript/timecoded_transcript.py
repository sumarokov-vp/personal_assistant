from typing import Any

from src.voice_recognition.models.transcript_segment import TranscriptSegment

SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60


class TimecodedTranscript:
    def __init__(self, result: dict[str, Any]) -> None:
        segments = [
            TranscriptSegment.model_validate(raw) for raw in result.get("segments", [])
        ]
        self._lines = [_line(segment) for segment in segments if segment.text.strip()]

    @property
    def text(self) -> str:
        return "".join(self._lines)

    def parts(self, max_chars: int) -> list[str]:
        parts: list[str] = []
        current = ""
        for line in self._lines:
            if current and len(current) + len(line) > max_chars:
                parts.append(current)
                current = ""
            current += line
        if current:
            parts.append(current)
        return parts


def _line(segment: TranscriptSegment) -> str:
    return f"[{_timecode(segment.start)}] {segment.text.strip()}\n"


def _timecode(seconds: float) -> str:
    whole = max(int(seconds), 0)
    hours, rest = divmod(whole, SECONDS_PER_HOUR)
    minutes, secs = divmod(rest, SECONDS_PER_MINUTE)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

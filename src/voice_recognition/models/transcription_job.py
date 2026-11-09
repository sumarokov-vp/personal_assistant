from typing import Any

from pydantic import BaseModel

from src.voice_recognition.models.transcription_status import TranscriptionStatus


class TranscriptionJob(BaseModel):
    job_id: str
    status: TranscriptionStatus
    result: dict[str, Any] | None = None
    error: str | None = None

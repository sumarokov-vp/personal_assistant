from typing import Any

from pydantic import BaseModel, ConfigDict


class RecordedTranscript(BaseModel):
    model_config = ConfigDict(frozen=True)

    transcript_id: str
    recording_name: str
    transcript_path: str
    recorded_on: str
    result: dict[str, Any]

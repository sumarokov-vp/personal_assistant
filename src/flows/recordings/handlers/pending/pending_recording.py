from pydantic import BaseModel

from src.flows.recordings.handlers.recording_file import RecordingFile


class PendingRecording(BaseModel):
    intake_id: str
    chat_id: int
    recording: RecordingFile

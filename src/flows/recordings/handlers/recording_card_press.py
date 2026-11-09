from pydantic import BaseModel

from src.flows.recordings.handlers.pending.pending_recording import PendingRecording


class RecordingCardPress(BaseModel):
    pending: PendingRecording
    chat_id: int
    message_id: int

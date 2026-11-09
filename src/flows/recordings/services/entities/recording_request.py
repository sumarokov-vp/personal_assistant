from pydantic import BaseModel, ConfigDict


class RecordingRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_id: str
    file_name: str
    size_bytes: int
    chat_id: int

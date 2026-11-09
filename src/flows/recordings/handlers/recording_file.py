from pydantic import BaseModel


class RecordingFile(BaseModel):
    file_id: str
    file_name: str
    size_bytes: int

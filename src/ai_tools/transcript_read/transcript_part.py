from pydantic import BaseModel


class TranscriptPart(BaseModel):
    path: str
    parts: int
    part: int
    text: str

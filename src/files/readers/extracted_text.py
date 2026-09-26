from pydantic import BaseModel


class ExtractedText(BaseModel):
    text: str
    truncated: bool

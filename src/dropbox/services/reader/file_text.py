from pydantic import BaseModel


class FileText(BaseModel):
    path: str
    text: str
    truncated: bool

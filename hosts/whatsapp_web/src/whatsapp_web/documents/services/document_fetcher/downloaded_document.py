from pydantic import BaseModel, ConfigDict


class DownloadedDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    shown_name: str
    content: bytes

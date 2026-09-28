from pydantic import BaseModel, ConfigDict


class FetchedDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_name: str
    content: bytes
    content_type: str
    elapsed_ms: int

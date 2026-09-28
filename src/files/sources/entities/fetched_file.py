from pydantic import BaseModel, ConfigDict


class FetchedFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: bytes
    name: str
    media_type: str
    origin: str

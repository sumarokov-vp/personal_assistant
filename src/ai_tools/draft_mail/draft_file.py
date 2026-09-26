from pydantic import BaseModel, ConfigDict


class DraftFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    media_type: str
    content: bytes

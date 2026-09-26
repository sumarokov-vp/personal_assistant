from pydantic import BaseModel, ConfigDict


class WorkFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    media_type: str
    size: int
    source: str

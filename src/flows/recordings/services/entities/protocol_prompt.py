from pydantic import BaseModel, ConfigDict


class ProtocolPrompt(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    request: str
    url: str

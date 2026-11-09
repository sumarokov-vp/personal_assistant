from pydantic import BaseModel, ConfigDict


class ProtocolPrompts(BaseModel):
    model_config = ConfigDict(frozen=True)

    protocol: str
    notes: str

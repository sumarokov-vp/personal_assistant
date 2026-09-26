from pydantic import BaseModel, ConfigDict


class PlannedMove(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    target: str

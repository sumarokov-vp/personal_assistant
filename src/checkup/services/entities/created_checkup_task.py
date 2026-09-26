from pydantic import BaseModel, ConfigDict


class CreatedCheckupTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    content: str
    due: str
    reason: str
    url: str

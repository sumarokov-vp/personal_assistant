from pydantic import BaseModel, ConfigDict


class CallbackButton(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    data: str

from pydantic import BaseModel, ConfigDict


class UrlButton(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    url: str

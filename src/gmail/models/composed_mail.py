from pydantic import BaseModel, ConfigDict


class ComposedMail(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: bytes
    attached: list[str]
    left_out: list[str]

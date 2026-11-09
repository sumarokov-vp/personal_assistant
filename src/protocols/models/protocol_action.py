from pydantic import BaseModel, Field


class ProtocolAction(BaseModel):
    what: str = Field(min_length=1)
    who: str = Field(min_length=1)
    due: str = ""

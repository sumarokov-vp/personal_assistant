from pydantic import BaseModel, Field

from src.colleague_mail.models.assistant_key import ASSISTANT_KEY_PATTERN


class Colleague(BaseModel):
    key: str = Field(pattern=ASSISTANT_KEY_PATTERN)
    name: str = Field(min_length=1)
    editor: bool = False

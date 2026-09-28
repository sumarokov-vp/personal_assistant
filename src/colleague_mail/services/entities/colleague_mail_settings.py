from pathlib import Path
from typing import Self
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, Field, model_validator

from src.colleague_mail.models.assistant_key import (
    ASSISTANT_ACCOUNT_PREFIX,
    ASSISTANT_KEY_PATTERN,
)


class ColleagueMailSettings(BaseModel):
    mail_url: str
    key: str = Field(pattern=ASSISTANT_KEY_PATTERN)
    directory_file: Path | None

    @property
    def account(self) -> str:
        return f"{ASSISTANT_ACCOUNT_PREFIX}{self.key}"

    @property
    def inbox(self) -> str:
        return f"inbox.{self.key}"

    @model_validator(mode="after")
    def login_matches_key(self) -> Self:
        login = unquote(urlsplit(self.mail_url).username or "")
        if login != self.account:
            raise ValueError(
                f"ASSISTANT_MAIL_URL logs in as {login!r}, "
                f"ASSISTANT_KEY={self.key} needs {self.account!r}"
            )
        return self

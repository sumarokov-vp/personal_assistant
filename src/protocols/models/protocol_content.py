import re
from datetime import date
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.protocols.models.discussion_topic import DiscussionTopic
from src.protocols.models.protocol_action import ProtocolAction
from src.protocols.models.protocol_kind import ProtocolKind

RUSSIAN_DATE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")


class ProtocolContent(BaseModel):
    kind: ProtocolKind
    title: str = Field(min_length=1)
    date: str
    parties: dict[str, list[str]] = {}
    agenda: list[str] = []
    discussion: list[DiscussionTopic] = []
    agreements: list[str] = []
    actions: list[ProtocolAction] = []
    open_questions: list[str] = []

    @field_validator("date")
    @classmethod
    def _date_is_russian_format(cls, value: str) -> str:
        _calendar_date(value)
        return value

    @model_validator(mode="after")
    def _call_has_no_agenda(self) -> Self:
        if self.kind == ProtocolKind.CALL and (self.agenda or self.discussion):
            raise ValueError(
                "У протокола звонка нет повестки и обсуждения: "
                "договорённости — в agreements, поручения — в actions"
            )
        return self

    @property
    def iso_date(self) -> str:
        return _calendar_date(self.date).isoformat()


def _calendar_date(value: str) -> date:
    match = RUSSIAN_DATE.match(value)
    if match is None:
        raise ValueError(f"Дата «{value}» — нужен формат ДД.ММ.ГГГГ")
    day, month, year = (int(part) for part in match.groups())
    return date(year, month, day)

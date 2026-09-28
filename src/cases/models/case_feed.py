from pydantic import BaseModel

from src.cases.models.case import Case
from src.cases.models.case_event import CaseEvent


class CaseFeed(BaseModel):
    case: Case
    events: list[CaseEvent]
    has_earlier: bool

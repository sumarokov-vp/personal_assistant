from pydantic import BaseModel

from src.cases.models.case_event import CaseEvent


class EventAddition(BaseModel):
    event: CaseEvent
    created: bool

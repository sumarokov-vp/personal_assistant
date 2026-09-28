from typing import Protocol

from src.cases.models.event_addition import EventAddition
from src.cases.models.new_event import NewEvent


class ITaskEventAdder(Protocol):
    def add_event(self, case_id: str, event: NewEvent) -> EventAddition: ...

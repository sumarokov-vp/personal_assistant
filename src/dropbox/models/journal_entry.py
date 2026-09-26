from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.dropbox.models.journal_action import JournalAction


class JournalEntry(BaseModel):
    action: JournalAction
    plan_id: UUID | None
    source: str | None
    target: str
    reason: str | None
    created_at: datetime

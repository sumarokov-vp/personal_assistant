from pydantic import BaseModel, ConfigDict

from src.checkup.models.checkup_journal_entry import CheckupJournalEntry
from src.checkup.services.checkup_actions.checkup_action_outcome import (
    CheckupActionOutcome,
)


class CheckupActionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: CheckupActionOutcome
    journal_entry: CheckupJournalEntry

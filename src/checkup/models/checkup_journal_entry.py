from datetime import date

from pydantic import BaseModel, ConfigDict

from src.memory.models.cell_text import CellText, RequiredCellText


class CheckupJournalEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: RequiredCellText
    when: date
    done: RequiredCellText
    task: CellText = ""
    reason: CellText = ""

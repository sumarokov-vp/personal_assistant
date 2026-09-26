from datetime import date

from pydantic import BaseModel, ConfigDict

from src.memory.models.cell_text import CellText, RequiredCellText


class Deadline(BaseModel):
    model_config = ConfigDict(frozen=True)

    what: RequiredCellText
    whose: RequiredCellText
    expires: date
    renewal: CellText = ""
    duration: CellText = ""
    source: CellText = ""
    updated: date | None = None

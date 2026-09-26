from datetime import date

from pydantic import BaseModel, ConfigDict

from src.memory.models.cell_text import CellText, RequiredCellText


class Whereabouts(BaseModel):
    model_config = ConfigDict(frozen=True)

    since: date
    until: date | None = None
    place: RequiredCellText
    purpose: CellText = ""
    source: CellText = ""

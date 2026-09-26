from datetime import date

from pydantic import BaseModel, ConfigDict

from src.memory.models.cell_text import CellText, RequiredCellText
from src.memory.models.commitment_status import CommitmentStatus


class Commitment(BaseModel):
    model_config = ConfigDict(frozen=True)

    what: RequiredCellText
    parties: RequiredCellText
    due: date | None = None
    status: CommitmentStatus = CommitmentStatus.OPEN
    source: CellText = ""

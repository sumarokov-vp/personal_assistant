from datetime import datetime

from pydantic import BaseModel


class SearchHit(BaseModel):
    path: str
    is_folder: bool
    size: int
    modified_at: datetime

from datetime import datetime

from pydantic import BaseModel


class TaskComment(BaseModel):
    text: str
    posted_at: datetime

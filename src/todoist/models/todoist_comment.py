from pydantic import BaseModel


class TodoistComment(BaseModel):
    id: str
    content: str
    posted_at: str

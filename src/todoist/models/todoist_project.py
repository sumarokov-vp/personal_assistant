from pydantic import BaseModel


class TodoistProject(BaseModel):
    id: str
    name: str

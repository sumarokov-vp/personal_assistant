from pydantic import BaseModel


class CaseRef(BaseModel):
    id: str
    title: str

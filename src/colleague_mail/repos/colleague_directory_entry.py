from pydantic import BaseModel, ConfigDict, Field


class ColleagueDirectoryEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)
    editor: bool = False

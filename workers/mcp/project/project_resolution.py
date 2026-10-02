from typing import Literal

from pydantic import BaseModel

ProjectSource = Literal["header", "param", "none"]

PROJECT_RESOLUTION_STATE_KEY = "project_resolution"


class ProjectResolution(BaseModel):
    project: str | None
    source: ProjectSource
    allowed: bool

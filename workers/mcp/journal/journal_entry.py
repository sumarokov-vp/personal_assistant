from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from workers.mcp.project.project_resolution import ProjectSource

Outcome = Literal["ok", "error", "denied"]


class JournalEntry(BaseModel):
    time: datetime
    method: str | None
    client: dict[str, Any] | None
    headers: dict[str, str]
    meta: dict[str, Any] | None
    tool: str | None
    project: str | None
    project_source: ProjectSource | None
    outcome: Outcome

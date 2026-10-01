from pydantic import AwareDatetime, BaseModel


class NewSchedule(BaseModel):
    case_id: str
    instruction: str
    at: AwareDatetime | None = None
    cron: str | None = None
    timezone: str | None = None

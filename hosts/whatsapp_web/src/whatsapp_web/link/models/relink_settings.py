from pydantic import BaseModel, ConfigDict

FIFTEEN_MINUTES = 15 * 60
SIX_HOURS = 6 * 60 * 60
ONE_DAY = 24 * 60 * 60


class RelinkSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    phone: str | None
    window_seconds: float = FIFTEEN_MINUTES
    max_codes: int = 3
    poll_seconds: float = 15
    cooldown_seconds: float = SIX_HOURS
    check_interval_seconds: float = ONE_DAY

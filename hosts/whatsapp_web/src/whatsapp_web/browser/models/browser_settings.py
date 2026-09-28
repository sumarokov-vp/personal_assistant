from pathlib import Path

from pydantic import BaseModel, ConfigDict

SPIKE_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


class BrowserSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_dir: Path
    headless: bool = True
    idle_seconds: float = 600
    user_agent: str = SPIKE_USER_AGENT
    locale: str = "ru-RU"

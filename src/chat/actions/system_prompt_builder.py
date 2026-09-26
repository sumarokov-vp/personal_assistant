from datetime import datetime
from zoneinfo import ZoneInfo


class SystemPromptBuilder:
    def __init__(self, template: str, timezone: ZoneInfo) -> None:
        self.template = template
        self.timezone = timezone

    def build(self) -> str:
        now = datetime.now(tz=self.timezone)
        return (
            self.template.replace("{today}", now.strftime("%d.%m.%Y"))
            .replace("{now}", now.strftime("%H:%M"))
            .replace("{timezone}", self.timezone.key)
        )

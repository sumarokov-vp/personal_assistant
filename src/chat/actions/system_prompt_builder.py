import re
from collections.abc import Iterable
from datetime import datetime
from zoneinfo import ZoneInfo

CONNECTOR_SECTION = re.compile(
    r"^<!-- connector:(?P<key>[a-z_]+) -->\n(?P<body>.*?)^<!-- /connector:(?P=key) -->\n",
    re.MULTILINE | re.DOTALL,
)
BLANK_LINES_RUN = re.compile(r"\n{3,}")


class SystemPromptBuilder:
    def __init__(
        self,
        template: str,
        timezone: ZoneInfo,
        connectors: Iterable[str] = (),
    ) -> None:
        self.template = self._keep_sections_of(template, frozenset(connectors))
        self.timezone = timezone

    def build(self) -> str:
        now = datetime.now(tz=self.timezone)
        return (
            self.template.replace("{today}", now.strftime("%d.%m.%Y"))
            .replace("{now}", now.strftime("%H:%M"))
            .replace("{timezone}", self.timezone.key)
        )

    @staticmethod
    def _keep_sections_of(template: str, connectors: frozenset[str]) -> str:
        kept = CONNECTOR_SECTION.sub(
            lambda section: section["body"] if section["key"] in connectors else "",
            template,
        )
        return BLANK_LINES_RUN.sub("\n\n", kept)

import calendar
import re
from dataclasses import dataclass
from datetime import date

from src.memory.repos.markdown_table.table_line import fold

KEY_FORMAT = "Что | Чьё | ДД.ММ.ГГГГ"

_DAY_FIRST = re.compile(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$")
_YEAR_FIRST = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _parse_date(text: str) -> date | None:
    day_first = _DAY_FIRST.match(text)
    year_first = _YEAR_FIRST.match(text)
    if day_first is not None:
        day, month, year = (int(part) for part in day_first.groups())
    elif year_first is not None:
        year, month, day = (int(part) for part in year_first.groups())
    else:
        return None
    if not 1 <= month <= 12 or not 1 <= day <= calendar.monthrange(year, month)[1]:
        return None
    return date(year, month, day)


@dataclass(frozen=True)
class CheckupKey:
    what: str
    whose: str
    expires: date

    @classmethod
    def parse(cls, raw: str) -> "CheckupKey | None":
        parts = [_collapse(part) for part in raw.replace("\\|", "|").split("|")]
        if len(parts) != 3 or not parts[0] or not parts[1]:
            return None
        expires = _parse_date(parts[2])
        if expires is None:
            return None
        return cls(what=parts[0], whose=parts[1], expires=expires)

    @property
    def text(self) -> str:
        return f"{self.what} | {self.whose} | {self.expires.strftime('%d.%m.%Y')}"

    @property
    def folded(self) -> str:
        return fold(self.text)

import calendar
import re
from datetime import date

_DATE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")


def parse_memory_date(text: str) -> date | None:
    match = _DATE.match(text.strip())
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    if not 1 <= month <= 12:
        return None
    if not 1 <= day <= calendar.monthrange(year, month)[1]:
        return None
    return date(year, month, day)


def format_memory_date(value: date | None) -> str:
    return "" if value is None else value.strftime("%d.%m.%Y")

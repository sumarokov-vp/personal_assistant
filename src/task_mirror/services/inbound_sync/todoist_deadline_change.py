from datetime import date
from typing import Any

DEADLINE_KEY = "deadline"
ISO_DATE_LENGTH = 10


class TodoistDeadlineChange:
    @staticmethod
    def touched(extra_data: dict[str, Any] | None) -> bool:
        return extra_data is not None and DEADLINE_KEY in extra_data

    @staticmethod
    def new_deadline(extra_data: dict[str, Any]) -> date | None:
        value = extra_data.get(DEADLINE_KEY)
        if isinstance(value, dict):
            value = value.get("date")
        if not isinstance(value, str) or len(value) < ISO_DATE_LENGTH:
            return None
        return date.fromisoformat(value[:ISO_DATE_LENGTH])

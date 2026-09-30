from datetime import date
from typing import Any

ISO_DATE_LENGTH = 10


class TodoistActivityDate:
    @staticmethod
    def touched(extra_data: dict[str, Any] | None, key: str) -> bool:
        return extra_data is not None and key in extra_data

    @staticmethod
    def new_value(extra_data: dict[str, Any], key: str) -> date | None:
        value = extra_data.get(key)
        if isinstance(value, dict):
            value = value.get("date")
        if not isinstance(value, str) or len(value) < ISO_DATE_LENGTH:
            return None
        return date.fromisoformat(value[:ISO_DATE_LENGTH])

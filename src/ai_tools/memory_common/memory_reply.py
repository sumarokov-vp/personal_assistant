import json
from datetime import date
from enum import Enum

from pydantic import BaseModel, ValidationError

from src.memory.repos import MemoryPageFormatError

PAGE_FORMAT_HINT = (
    "Таблицу на странице не найти: владелец, похоже, переименовал колонки. "
    "Запись не сделана — скажи об этом владельцу."
)


def entry_view(entry: BaseModel) -> dict[str, str]:
    return {name: _cell(value) for name, value in entry.model_dump().items()}


def success_reply(status: str, page: str, entry: BaseModel) -> str:
    return json.dumps(
        {"status": status, "page": page, "entry": entry_view(entry)},
        ensure_ascii=False,
    )


def error_view(page: str, error: Exception) -> dict[str, str]:
    return {"status": "error", "page": page, "message": _error_message(error)}


def error_reply(page: str, error: Exception) -> str:
    return json.dumps(error_view(page, error), ensure_ascii=False)


def _error_message(error: Exception) -> str:
    if isinstance(error, MemoryPageFormatError):
        return f"{PAGE_FORMAT_HINT} Замечания: {'; '.join(error.remarks)}"
    if isinstance(error, ValidationError):
        return "Неверные данные записи: " + "; ".join(
            f"{'.'.join(str(part) for part in detail['loc'])}: {detail['msg']}"
            for detail in error.errors()
        )
    return str(error)


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)

import re
from dataclasses import dataclass
from datetime import date

from src.checkup.services.entities import CreatedCheckupTask

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class CheckupReport:
    created: list[CreatedCheckupTask]
    model_summary: str

    def owner_message(self) -> str | None:
        if not self.created:
            return None
        lines = [f"Чекап поставил задачи в Todoist ({len(self.created)}):"]
        lines.extend(
            f"• {task.content} — до {_readable_due(task.due)}. {task.reason}"
            for task in self.created
        )
        return "\n".join(lines)

    def render(self) -> str:
        created = self.owner_message() or "Чекап завершён: новых задач нет."
        summary = self.model_summary.strip()
        return f"{created}\n\n{summary}" if summary else created


def _readable_due(due: str) -> str:
    iso = ISO_DATE.match(due)
    if iso is None:
        return due
    return date.fromisoformat(iso.group()).strftime("%d.%m.%Y")

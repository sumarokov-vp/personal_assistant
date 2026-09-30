from src.task_manager.models.task_search import TaskSearch
from src.todoist.services.entities.todoist_identity import ASSISTANT_LABEL

EVERY_ACTIVE_TASK = "no date | !no date"
FILTER_SPECIAL_CHARACTERS = "\\&|!(),:@#*"


class TodoistFilterQuery:
    @staticmethod
    def of(search: TaskSearch) -> str:
        conditions: list[str] = []
        if search.text:
            conditions.append(f"search: {_escaped(search.text)}")
        if search.due_before is not None:
            conditions.append(f"due before: {search.due_before.isoformat()}")
        if search.overdue:
            conditions.append("overdue")
        if search.by_assistant:
            conditions.append(f"@{ASSISTANT_LABEL}")
        return " & ".join(conditions) or EVERY_ACTIVE_TASK


def _escaped(text: str) -> str:
    return "".join(
        f"\\{symbol}" if symbol in FILTER_SPECIAL_CHARACTERS else symbol
        for symbol in text.strip()
    )

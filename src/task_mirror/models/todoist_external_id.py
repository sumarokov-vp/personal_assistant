TODOIST_PREFIX = "todoist:"
TODOIST_TASK_URL = "https://app.todoist.com/app/task/{task_id}"


class TodoistExternalId:
    @staticmethod
    def of(todoist_task_id: str) -> str:
        return f"{TODOIST_PREFIX}{todoist_task_id}"

    @staticmethod
    def todoist_task_id(external_id: str | None) -> str | None:
        if external_id is None or not external_id.startswith(TODOIST_PREFIX):
            return None
        return external_id.removeprefix(TODOIST_PREFIX) or None

    @staticmethod
    def url(todoist_task_id: str) -> str:
        return TODOIST_TASK_URL.format(task_id=todoist_task_id)

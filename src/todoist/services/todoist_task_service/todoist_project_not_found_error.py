class TodoistProjectNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Проект Todoist «{name}» не найден")
        self.name = name

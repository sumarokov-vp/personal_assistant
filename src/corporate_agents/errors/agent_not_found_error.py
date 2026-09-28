class AgentNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Агента «{name}» в каталоге нет")
        self.name = name

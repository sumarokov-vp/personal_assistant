from pathlib import Path


class TelegramSecretsFileError(ValueError):
    def __init__(self, path: Path, problem: str) -> None:
        super().__init__(f"Секрет-файл Telegram {path}: {problem}")
        self.path = path
        self.problem = problem
